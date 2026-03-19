import pandas as pd
import pystow
import tqdm
import json
import gc
import logging
from pathlib import Path
from mira.sources.sympy_ode.paper_extraction import get_template_model_from_pmid
from mira.modeling import Model
from mira.modeling.ode import OdeModel
from indra.literature.pubmed_client import (
    get_pmid_to_package_url_mapping,
    pmid_to_pmc_download_url,
)
from mira.metamodel import TemplateModel

HERE = Path(__file__).parent.resolve()
DATA_PATH = HERE / "extracted_papers"
POSITIVE_PATH = DATA_PATH / "positive"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_pmid_to_pmc_mapping_path() -> Path:
    """Get the path to the PMID-to-PMC mapping file."""
    return pystow.ensure(
        "mira", "paper_extraction", url=pmid_to_pmc_download_url
    )


def save_with_intermediates(template_model: TemplateModel, ode_data: dict, pmid: str):
    """
    Save both intermediate results and final model.
    Args:
        template_model (TemplateModel): The extracted template model.
        ode_data (dict): ODE extraction data.
        pmid (str): PubMed ID.
    """
    with open(POSITIVE_PATH / f"{pmid}_intermediates.json", 'w') as f:
        json.dump(ode_data, f, indent=2)
    with open(POSITIVE_PATH / f"{pmid}.json", 'w') as f:
        json.dump(template_model.model_dump(), f, indent=2)


def main():
    # Load the list of PMIDs for papers that were classified as relevant (positive) by the trained model.
    positive_papers = DATA_PATH / "positive_papers.tsv"
    df = pd.read_csv(positive_papers, sep='\t')

    pmid_to_download_mapping = get_pmid_to_package_url_mapping(
        get_pmid_to_pmc_mapping_path().as_posix()
    )

    # Track progress - append to CSV after each success
    progress_file = DATA_PATH / "extraction_progress.csv"
    processed_pmids = set()
    if progress_file.exists():
        progress_df = pd.read_csv(progress_file, header=None, names=['pmid', 'status', 'error'], quotechar='"', on_bad_lines='skip')
        processed_pmids = set(progress_df['pmid'].astype(str))
        logger.info(f"Found {len(processed_pmids)} already processed PMIDs")

    for idx, row in tqdm.tqdm(df.iterrows(), total=len(df)):
        pmid = str(row["PMID"])
        # Skip if already processed
        if pmid in processed_pmids:
            logger.info(f"{idx}: PMID {pmid} already attempted, skipping...")
            continue
        try:
            logger.info(f"#{idx} ------- Processing PMID {pmid}...")
            tm, ode_str = get_template_model_from_pmid(pmid, "image", pmid_to_download_mapping)
            logger.info(f"PMID {pmid} ODE:\n{ode_str}\n")
            save_with_intermediates(tm, {"ode": ode_str}, pmid)
            # Create OdeModel only for validation, then release
            om = OdeModel(Model(tm), initialized=True)
            # Explicit cleanup. Memory usage gets high if there are many papers.
            del om, tm  

            with open(progress_file, 'a') as f:
                f.write(f"{pmid},success\n")

        except Exception as e:
            logger.warning(f"Failed to extract model for PMID {pmid}: {e}")
            with open(progress_file, 'a') as f:
                f.write(f"{pmid},failed,{str(e)}\n")
            continue
        finally:
            gc.collect()

if __name__ == "__main__":
    main()