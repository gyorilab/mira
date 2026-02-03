import os
from pathlib import Path
from setfit import SetFitModel

from mira.sources.sympy_ode.paper_relevance_ranking.utils import (
    download_papers,
    get_pmid_pmc_download_mapping,
    extract_and_get_nxml_paths,
    parse_nxml,
)

HERE = Path(__file__).parent.resolve()

TEST_DATA_PATH = HERE / "testing_data"
TEST_DATA_PATH.mkdir(parents=True, exist_ok=True)


def load_setfit_model(model_path=None):
    """
    Load a saved SetFit model.

    Args:
        model_path (str): Path to the saved model (optional)

    Returns:
        SetFitModel: Loaded SetFit model
    """
    if model_path is None:
        # Default model path
        model_path = (HERE / "pubmed_classifier").as_posix()

    print(f"📂 Loading SetFit model from: {model_path}")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at: {model_path}")

    model = SetFitModel.from_pretrained(model_path)

    return model


def test_model_on_samples(texts, true_labels, pmids, model_path=None):
    """
    Test the loaded model on sample sentences.

    Args:
        model_path (str): Path to the saved model (optional)
    """
    model = load_setfit_model(model_path)
    confidences = model.predict_proba(texts)
    prediction_labels = confidences.argmax(dim=1).tolist()
    num_correct = sum(p == t for p, t in zip(prediction_labels, true_labels))
    incorrect_pmids = [
        (pmid, p, t)
        for pmid, p, t in zip(pmids, prediction_labels, true_labels)
        if p != t
    ]

    accuracy = num_correct / len(true_labels)
    print(f"Accuracy: {accuracy:.2%}")

    for incorrect_tuple in incorrect_pmids:
        print(
            f"Incorrectly classified pmid: {incorrect_tuple[0]}. It should be classified as {incorrect_tuple[2]} but is classified as {incorrect_tuple[1]}"
        )

    # Print formatted results table
    print("\nPrediction Results:")
    print("=" * 70)
    print(
        f"{'PMID':<12} {'P(neg)':<8} {'P(pos)':<8} {'Pred':<6} {'True':<6} {'Status'}")
    print("-" * 70)

    for pmid, probs, pred, true in zip(pmids, confidences, prediction_labels,
                                       true_labels):
        p_neg, p_pos = probs[0].item(), probs[1].item()
        pred_label = "Pos" if pred == 1 else "Neg"
        true_label = "Pos" if true == 1 else "Neg"
        status = "✓" if pred == true else "✗"

        print(
            f"{pmid:<12} {p_neg:<8.3f} {p_pos:<8.3f} {pred_label:<6} {true_label:<6} {status}")

    print("=" * 70)


def main():
    """Main function to test the model."""
    pmid_to_download_mapping = get_pmid_pmc_download_mapping()

    #  BIOMD972, BIOMD974, BIOMD976, BIOMD977, BIOMD978, BIOMD979, BIOMD983, BIOMD991
    positive_pmids = [
        "32099934",
        "32574303",
        "32834656",
        "32834603",
        "32706790",
        "32982082",
        "32958091",
        "32834593",
        "21656080",
    ]

    # first negative example is close to decision boundary, second isn't
    negative_pmids = ["30642334", "36105506"]
    pmids = positive_pmids + negative_pmids
    labels = [1] * len(positive_pmids) + [0] * len(negative_pmids)
    download_papers(pmids, TEST_DATA_PATH, pmid_to_download_mapping)

    nxml_paths = extract_and_get_nxml_paths(
        TEST_DATA_PATH, pmids, pmid_to_download_mapping
    )

    text_content = [parse_nxml(nxml_fp) for nxml_fp in nxml_paths]

    test_model_on_samples(text_content, labels, pmids)


if __name__ == "__main__":
    main()
