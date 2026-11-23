import logging
import re

from bs4 import BeautifulSoup, Tag

from indra.literature.pmc_client import _get_s3_artifact
from mira.sources.sympy_ode.scenario_extraction import PaperTable
from .base import Extractor

logger = logging.getLogger(__name__)


class XmlExtractor(Extractor):
    """Extract equations from a paper's PMC XML via the PMC S3 artifact."""

    def __init__(self, pmid, pmc):
        super().__init__(pmid)
        self.pmc = pmc
        self.xml = None

    def get_xml(self) -> str:
        """Return the paper's XML, downloading it from PMC S3 only once.
        """
        if self.xml is None:
            resp = _get_s3_artifact(self.pmc, "xml")
            try:
                self.xml = resp.content.decode("utf-8")
            except UnicodeDecodeError:
                logger.warning("PMC %s XML is not valid UTF-8; falling back to "
                               "the guessed encoding %s", self.pmc,
                               resp.apparent_encoding)
                self.xml = resp.text
        return self.xml

    def get_pipeline_inputs(self):
        logger.info("running xml")
        eqns = []
        soup = BeautifulSoup(self.get_xml(), 'lxml-xml')

        tex_blocks = soup.find_all('tex-math')
        eq_type = "latex"
        if len(tex_blocks) > 0:
            for block in tex_blocks:
                raw = block.get_text()
                # Extract just the math content between \begin{document} and
                # \end{document}
                match = re.search(r'\\begin\{document\}(.*?)\\end\{document\}',
                                  raw, re.DOTALL)
                if match:
                    latex = match.group(1).strip()
                    eqns.append(latex)
        else:
            math_blocks = soup.find_all('disp-formula')
            eq_type = "text"
            for block in math_blocks:
                eqns.append(block.get_text())

        markdown_text = "\n\n".join(
            [
                str((equation, eq_type))
                for equation in eqns
            ]
        )

        self.extraction_file = "No intermediate created"
        return {"content_type": "text", "text_content": markdown_text}


    def raw_xml(self, el: Tag | None) -> str:
        """The inner XML of one cell (or caption / footnote element), unrendered.

        Tabs, carriage returns and newlines are replaced with spaces, and the
        string is stripped. If the element is None, return the empty string.
        """
        if el is None:
            return ""
        inner = "".join(map(str, el.contents))
        return inner.translate(str.maketrans("\t\r\n", "   ")).strip()


    def _expand_rows(self, trs: list[Tag]) -> list[list[str]]:
        """Lay rows out on a rectangular grid, honouring rowspan/colspan.

        A spanning cell's text goes in its top-left slot only; the other slots it
        covers are left empty rather than filled with copies.
        """

        def _span(cell: Tag, attr: str) -> int:
                try:
                    return max(1, int(cell.get(attr, 1)))
                except ValueError:
                    return 1
                
        grid: dict[tuple[int, int], str] = {}
        for r, tr in enumerate(trs):
            c = 0
            for cell in tr.find_all(["td", "th"], recursive=False):
                while (r, c) in grid:  # slot already taken by a rowspan from above
                    c += 1
                colspan = _span(cell, "colspan")
                for dr in range(_span(cell, "rowspan")):
                    for dc in range(colspan):
                        grid[r + dr, c + dc] = ""
                grid[r, c] = self.raw_xml(cell)
                c += colspan
        width = max((c for _, c in grid), default=-1) + 1
        return [[grid.get((r, c), "") for c in range(width)] for r in range(len(trs))]


    def parse_table_wrap(self, tw: Tag, index: int = 1) -> PaperTable:
        """Return a PaperTable from one <table-wrap> element.
        """
        t = PaperTable(table_id=tw.get("id") or f"table{index}",
                       caption=self.raw_xml(tw.find("caption")))
        footnotes = []
        if foot := tw.find("table-wrap-foot"):
            entries = foot.find_all("fn") or [
                p for p in foot.find_all("p") if not p.find("p")]
            footnotes = ([s for s in map(self.raw_xml, entries) if s]
                         or [s for s in [self.raw_xml(foot)] if s])
            t.footer = " || ".join(footnotes)

        table = tw.find("table")
        if table is None:
            t.has_table = False
            if tw.find(["graphic", "inline-graphic", "media"]):
                logger.info("PMID %s table %s: no <table>, body is an image",
                            self.pmid, t.table_id)
            else:
                logger.info("PMID %s table %s: no <table> and no <graphic>",
                            self.pmid, t.table_id)
            return t

        thead = table.find("thead", recursive=False)
        head_trs = thead.find_all("tr", recursive=False) if thead else []
        body_trs = [tr for sec in table.find_all("tbody", recursive=False) or [table]
                    for tr in sec.find_all("tr", recursive=False)]
        grid = self._expand_rows(head_trs + body_trs)

        header_rows, body_rows = grid[:len(head_trs)], grid[len(head_trs):]
        t.header = [" | ".join(row) for row in header_rows]
        title = " ".join(filter(None, (self.raw_xml(tw.find("label")),
                                       t.caption)))
        lines = [f"=== table_id: {t.table_id}"]
        if title:
            lines.append(f"# {title}")
        lines += ["\t".join(row) for row in header_rows + body_rows]
        if footnotes:
            lines.append("# footnotes: " + " || ".join(footnotes))
        t.content = "\n".join(lines)

        if not body_rows:
            t.has_table = False
            logger.info("PMID %s table %s: empty body", self.pmid, t.table_id)

        return t


    def find_tables(self, xml: str | None = None) -> list[PaperTable]:
        """Tables of the paper; uses the XML already downloaded for the ODEs."""
        soup = BeautifulSoup(xml if xml is not None else self.get_xml(),
                             "lxml-xml")
        return [self.parse_table_wrap(tw, i) for i, tw in
                enumerate(soup.find_all("table-wrap"), start=1)]