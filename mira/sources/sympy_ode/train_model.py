import tarfile
from lxml import etree
from pathlib import Path
from copy import deepcopy


from setfit import SetFitModel
from indra.literature.pubmed_client import (
    get_pmid_to_package_url_mapping,
    download_package_for_pmids,
)

from mira.sources.sympy_ode.paper_extraction import get_pmid_to_pmc_mapping_path

HERE = Path(__name__).parent.resolve()
NEGATIVE_PATH = HERE / "training_data" / "negative"
POSITIVE_PATH = HERE / "training_data" / "positive"
MODEL_SAVE_PATH = HERE / "pubmed_classifier"

NEGATIVE_PATH.mkdir(parents=True, exist_ok=True)
POSITIVE_PATH.mkdir(parents=True, exist_ok=True)


def download_papers(pmid_list, output_dir, mapping):
    uncached_pmids = []
    for pmid in pmid_list:
        pmc_id = Path(mapping[pmid]).stem.split(".")[0]

        # Test to see if the pmc directory for a single paper is in the
        # respective class training data folder
        # We unzip the downloaded the pmc folder later
        pmc_exists = any(pmc_id in str(item) for item in output_dir.rglob("*"))
        if not pmc_exists:
            uncached_pmids.append(pmid)

    if uncached_pmids:
        download_package_for_pmids(
            uncached_pmids, output_dir.as_posix(), mapping
        )


def extract_and_get_nxml_paths(dir_path):
    tar_files = list(dir_path.glob("*.tar.gz"))

    nxml_paths = []

    for tar_file in tar_files:

        with tarfile.open(tar_file, "r:gz") as tar:
            tar.extractall(path=dir_path)

        extracted_name = tar_file.stem.replace(".tar", "")
        extracted_subdirectory = dir_path / extracted_name

        nxml_file = list(extracted_subdirectory.glob("**/*.nxml"))[0]
        nxml_paths.append(nxml_file)

    return nxml_paths


def get_clean_text(element):
    """Extract text and completely remove formula elements"""
    if element is None:
        return ""

    elem = deepcopy(element)

    # Remove ALL formula-related tags
    # These contain the LaTeX code
    for tag in [
        "inline-formula",
        "disp-formula",
        "tex-math",
        "mml:math",
        "alternatives",
    ]:
        for formula_elem in elem.xpath(
            f".//{tag}",
            namespaces={"mml": "http://www.w3.org/1998/Math/MathML"},
        ):
            # Remove the entire element
            parent = formula_elem.getparent()
            if parent is not None:
                parent.remove(formula_elem)

    # Extract remaining text
    text = " ".join(elem.itertext()).strip()

    # Clean up multiple spaces
    text = " ".join(text.split())

    return text


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

    # Extract body
    body_elem = root.find(".//body")
    body = get_clean_text(body_elem)

    # Combine
    full_text = f"{title}\n\n{abstract}\n\n{body}"

    return full_text


def train_save_model(positive_nxml_paths, negative_nxml_paths, num_epochs=3):
    full_text = {"positive": [], "negative": []}
    for positive_nxml_fp in positive_nxml_paths:
        full_text["positive"].append(parse_nxml(positive_nxml_fp))
    for negative_nxml_fp in negative_nxml_paths:
        full_text["negative"].append(parse_nxml(negative_nxml_fp))
    training_samples = full_text["positive"] + full_text["negative"]
    training_labels = [1] * len(positive_nxml_paths) + [0] * len(
        negative_nxml_paths
    )

    model = SetFitModel.from_pretrained("sentence-transformers/allenai-specter")

    model.fit(training_samples, training_labels, num_epochs=num_epochs)
    model_save_path = str(Path(__file__).parent / "pubmed_classifier")
    print(f"💾 Saving trained model to: {model_save_path}")
    model.save_pretrained(model_save_path)


def main():

    # papers that represent and define a single specific ODE model for
    # a use-case/simulation/scenario
    positive_pmids = [
        "32322102",
        "32616574",
        "32289100",
        "32341628",
        "32735581",
        "32219006",
        "32703315",
        "32046137",
        "36000145",
        "29928736",
    ]

    # I tried to get papers that would be close on the decision boundary like
    # papers that review and define multiple ODE models.
    negative_pmids = [
        "36000145",
        "29928736",
        "34621252",
        "28870213",
        "38792730",
        "30050523",
        "29593941",
        "37997927",
    ]

    pmid_to_download_mapping = get_pmid_to_package_url_mapping(
        get_pmid_to_pmc_mapping_path().as_posix()
    )

    download_papers(positive_pmids, POSITIVE_PATH, pmid_to_download_mapping)
    download_papers(negative_pmids, NEGATIVE_PATH, pmid_to_download_mapping)

    positive_nxml_paths = extract_and_get_nxml_paths(POSITIVE_PATH)
    negative_nxml_paths = extract_and_get_nxml_paths(NEGATIVE_PATH)

    train_save_model(positive_nxml_paths, negative_nxml_paths)


if __name__ == "__main__":
    main()
