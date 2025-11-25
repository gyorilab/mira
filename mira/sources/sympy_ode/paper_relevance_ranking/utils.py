from pathlib import Path
from lxml import etree

import tarfile
from indra.literature.pubmed_client import (
    get_pmid_to_package_url_mapping,
    download_package_for_pmids,
)

from mira.sources.sympy_ode.paper_extraction import get_pmid_to_pmc_mapping_path


def get_pmid_pmc_download_mapping():
    return get_pmid_to_package_url_mapping(
        get_pmid_to_pmc_mapping_path().as_posix()
    )


def get_pmc_id(pmc_download_link):
    return Path(pmc_download_link).stem.split(".")[0]


def download_papers(pmid_list, output_dir, mapping):
    uncached_pmids = []
    for pmid in pmid_list:
        pmc_id = get_pmc_id(mapping[pmid])

        # Test to see if the pmc directory for a single paper is in the
        # respective class training data folder
        # We unzip and extract the downloaded the pmc folder later
        pmc_exists = any(pmc_id in str(item) for item in output_dir.rglob("*"))
        if not pmc_exists:
            uncached_pmids.append(pmid)

    if uncached_pmids:
        download_package_for_pmids(
            uncached_pmids, output_dir.as_posix(), mapping
        )


def extract_and_get_nxml_paths(dir_path, pmids, mapping):
    tar_files = list(dir_path.glob("*.tar.gz"))

    # Build a dictionary: pmc_id -> nxml_path
    pmc_to_nxml = {}

    for tar_file in tar_files:
        with tarfile.open(tar_file, "r:gz") as tar:
            tar.extractall(path=dir_path)

        extracted_name = tar_file.stem.replace(".tar", "")
        extracted_subdirectory = dir_path / extracted_name

        nxml_file = list(extracted_subdirectory.glob("**/*.nxml"))[0]
        pmc_to_nxml[extracted_name] = nxml_file

    # Return paths in the SAME ORDER as pmids
    nxml_paths = []
    for pmid in pmids:
        pmc_id = get_pmc_id(mapping[pmid])
        if pmc_id in pmc_to_nxml:
            nxml_paths.append(pmc_to_nxml[pmc_id])
        else:
            raise ValueError(
                f"PMID {pmid} (PMC {pmc_id}) not found in downloaded files")

    return nxml_paths


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
