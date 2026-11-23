from lxml import etree

from indra.literature.pmc_client import get_xml_s3, id_lookup


def get_xml_paths(pmids, output_dir):
    """Return the paths of the PMC XML files of the given PMIDs.

    XML files not yet in ``output_dir`` are downloaded from the PMC Cloud
    S3 bucket and saved as ``<PMID>.xml``.
    """
    paths = []
    for pmid in pmids:
        path = output_dir / f"{pmid}.xml"
        if not path.exists():
            pmcid = id_lookup(pmid, "pmid").get("pmcid")
            xml = get_xml_s3(pmcid) if pmcid else None
            if xml is None:
                raise ValueError(f"No PMC XML found for PMID {pmid}")
            output_dir.mkdir(parents=True, exist_ok=True)
            path.write_text(xml)
        paths.append(path)
    return paths


def get_clean_text(element):
    if element is None:
        return ""
    for tag in [
        "inline-formula",
        "disp-formula",
        "tex-math",
        "mml:math",
        "alternatives",
    ]:
        for formula_elem in element.xpath(
            f".//{tag}",
            namespaces={"mml": "http://www.w3.org/1998/Math/MathML"},
        ):
            parent = formula_elem.getparent()
            if parent is not None:
                parent.remove(formula_elem)

    text = " ".join(element.itertext()).strip()
    return " ".join(text.split())


def parse_nxml(nxml_fp):
    """Parse NXML and return clean text without LaTeX formulas"""
    tree = etree.parse(nxml_fp)
    root = tree.getroot()

    # Extract title
    title_elem = root.find(".//article-title")
    title = get_clean_text(title_elem)

    # Extract abstract
    abstract_elem = root.find(".//abstract")
    abstract = get_clean_text(abstract_elem)

    if title and abstract:
        full_text = f"{title}. {abstract}"
    elif title:
        full_text = title
    elif abstract:
        full_text = abstract
    else:
        full_text = ""  # Empty string if both are missing

    return full_text.strip()
