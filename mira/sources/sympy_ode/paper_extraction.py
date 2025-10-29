import tempfile
import tarfile
from pathlib import Path

import pandas as pd
import requests
from indra.literature.pubmed_client import download_package_for_pmid

from mira.sources.sympy_ode.agent_pipeline import run_multi_agent_pipeline
from mira.sources.sympy_ode.llm_util import execute_template_model_from_sympy_odes
from mira.openai import OpenAIClient


HERE = Path(__file__).parent.resolve()
PMID_TO_PMC_MAPPING_URL = (
    "https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_file_list.csv"
)
PMID_TO_PMC_MAPPING_PATH = HERE / "pmid_pmc_mapping.csv"


def get_mappings():
    if not PMID_TO_PMC_MAPPING_PATH.exists():
        print("here")
        response = requests.get(PMID_TO_PMC_MAPPING_URL, stream=True)
        response.raise_for_status()
        with open(PMID_TO_PMC_MAPPING_PATH, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    df = pd.read_csv(PMID_TO_PMC_MAPPING_PATH)
    return {
        pmid: f"https://ftp.ncbi.nlm.nih.gov/pub/pmc/{file}"
        for pmid, file in zip(df["PMID"], df["File"])
    }, {pmid: pmc for pmid, pmc in zip(df["PMID"], df["Accession ID"])}


def get_template_model_from_pmid(pmid):
    client = OpenAIClient()
    pmid_download_mapping, pmid_pmc_mapping = get_mappings()

    with tempfile.TemporaryDirectory() as temp_dir:
        pmc_content_path = download_package_for_pmid(
            pmid, temp_dir, pmid_download_mapping
        )
        with tarfile.open(pmc_content_path, "r:gz") as tar:
            tar.extractall(path=temp_dir)
        pmc = pmid_pmc_mapping[pmid]
        extracted_subdirectory = Path(temp_dir) / pmc

        nxml_file = list(extracted_subdirectory.glob("*.nxml"))[0]
        pdf_file = nxml_file.with_suffix('.pdf')

        ode_str, _ = run_multi_agent_pipeline(image_path=str(pdf_file),is_image=False)

        tm = execute_template_model_from_sympy_odes(ode_str=ode_str,
                                                    attempt_grounding=True,
                                                    client=client)
        return tm


