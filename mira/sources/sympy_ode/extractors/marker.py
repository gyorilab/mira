import gc
import logging

from .base import PdfExtractor

logger = logging.getLogger(__name__)


class MarkerExtractor(PdfExtractor):
    """Extract equations from a PDF using the Marker pipeline.

    Only text-mode extraction is supported; the equations are sent in text
    (LaTeX) format to the LLM.
    """

    supported_methods = {"text"}

    def get_pipeline_inputs(self):
        from bs4 import BeautifulSoup
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from marker.output import save_output

        out_dir = self.paper_base / "marker"
        html_file = out_dir / f"{self.pmid}.html"
        out_dir.mkdir(parents=True, exist_ok=True)

        # If the html file already exists, skip running the Marker pipeline and
        # just load the content list
        if html_file.is_file():
            with open(html_file) as f:
                soup = BeautifulSoup(f.read(), "html.parser")

        else:
            models = create_model_dict()
            converter = PdfConverter(
                artifact_dict=models,
                renderer="marker.renderers.html.HTMLRenderer"
            )
            rendered = converter(str(self.pdf_file))
            save_output(rendered, out_dir, fname_base=self.pmid)

            del converter
            del models
            del rendered
            gc.collect()

            with open(html_file) as f:
                soup = BeautifulSoup(f.read(), "html.parser")

        block_equations = soup.find_all("math", display="block")
        block_latex = [eq.get_text(strip=True) for eq in block_equations]

        equation_text = "\n\n".join([str((eq, "latex")) for eq in block_latex])

        self.extraction_file = str(html_file)
        return {"content_type": "text", "text_content": equation_text}
