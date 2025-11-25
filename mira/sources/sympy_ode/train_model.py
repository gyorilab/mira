import tarfile
from lxml import etree
from pathlib import Path


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

    nxml_paths = []
    pmc_id_set = set(get_pmc_id(mapping[pmid]) for pmid in pmids)
    for tar_file in tar_files:

        with tarfile.open(tar_file, "r:gz") as tar:
            tar.extractall(path=dir_path)

        extracted_name = tar_file.stem.replace(".tar", "")
        if extracted_name not in pmc_id_set:
            continue
        extracted_subdirectory = dir_path / extracted_name

        nxml_file = list(extracted_subdirectory.glob("**/*.nxml"))[0]
        nxml_paths.append(nxml_file)

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

    full_text = f"{title}. {abstract}".strip()

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

    positive_nxml_paths = extract_and_get_nxml_paths(
        POSITIVE_PATH, positive_pmids, pmid_to_download_mapping
    )
    negative_nxml_paths = extract_and_get_nxml_paths(
        NEGATIVE_PATH, negative_pmids, pmid_to_download_mapping
    )

    train_save_model(positive_nxml_paths, negative_nxml_paths)


if __name__ == "__main__":
    main()
