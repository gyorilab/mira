import os
from pathlib import Path
from setfit import SetFitModel

from mira.sources.sympy_ode.paper_relevance_ranking.utils import (
    download_papers,
    get_pmid_pmc_download_mapping,
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
    print("✅ Model loaded successfully")

    return model


def test_model_on_samples(pmids, model_path=None):
    """
    Test the loaded model on sample sentences.

    Args:
        model_path (str): Path to the saved model (optional)
    """
    model = load_setfit_model(model_path)


def main():
    """Main function to test the model."""
    pmid_to_download_mapping = get_pmid_pmc_download_mapping()
    pmids = []
    labels = []

    test_model_on_samples(pmids)


if __name__ == "__main__":
    main()
