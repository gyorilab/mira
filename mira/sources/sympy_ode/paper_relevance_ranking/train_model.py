from pathlib import Path

from setfit import SetFitModel

from mira.sources.sympy_ode.paper_relevance_ranking.utils import (
    parse_nxml,
    extract_and_get_nxml_paths,
    download_papers,
    get_pmid_pmc_download_mapping,
)

HERE = Path(__file__).parent.resolve()
NEGATIVE_PATH = HERE / "training_data" / "negative"
POSITIVE_PATH = HERE / "training_data" / "positive"
MODEL_SAVE_PATH = HERE / "pubmed_classifier"

NEGATIVE_PATH.mkdir(parents=True, exist_ok=True)
POSITIVE_PATH.mkdir(parents=True, exist_ok=True)


def train_save_model(positive_nxml_paths, negative_nxml_paths, num_epochs=3):
    full_text = {"positive": [], "negative": []}
    for positive_nxml_fp in positive_nxml_paths:
        text = parse_nxml(positive_nxml_fp)
        if text:
            full_text["positive"].append(parse_nxml(positive_nxml_fp))
    for negative_nxml_fp in negative_nxml_paths:
        text = parse_nxml(negative_nxml_fp)
        if text:
            full_text["negative"].append(parse_nxml(negative_nxml_fp))
    training_samples = full_text["positive"] + full_text["negative"]
    training_labels = [1] * len(positive_nxml_paths) + [0] * len(
        negative_nxml_paths
    )

    model = SetFitModel.from_pretrained("sentence-transformers/allenai-specter")

    model.fit(training_samples, training_labels, num_epochs=num_epochs)
    model_save_path = str(Path(__file__).parent / "pubmed_classifier")
    print(f"Saving trained model to: {model_save_path}")
    model.save_pretrained(model_save_path)


def main():

    # papers that represent and define a single specific ODE model for
    # a use-case/simulation/scenario (i.e. not review papers that define multiple ODE models.
    # Papers were also chosen to span different epidemiological domains and use-cases (e.g. COVID, HIV, Malaria, etc.) to encourage generalization of the model.
    positive_pmids = [
        "32322102",
        "32616574",
        "32289100",
        "34667829",
        "41057369",
        "37156899",
        "38635754",
        "38954691",
        "35369460",
        "40969323",
        "33869905",
    ]

    # I tried to get papers that would be close on the decision boundary like
    # papers that review and define multiple ODE models.
    negative_pmids = [
        "36000145",
        "29928736",
        "34621252",
        "28870213",
        "41165884",
        "41139290",
        "39946392",
        "38427667",
        "40845139",
    ]

    pmid_to_download_mapping = get_pmid_pmc_download_mapping()

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
