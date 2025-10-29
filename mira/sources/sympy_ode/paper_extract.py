from indra.literature.pubmed_client import download_package_for_pmid
import tarfile
import pandas as pd
import requests
from pathlib import Path

import tempfile


HERE = Path(__file__).parent.resolve()
PMID_TO_PMC_MAPPING_URL = "https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_file_list.csv"
PMID_TO_PMC_MAPPING_PATH = HERE / "pmid_pmc_mapping.csv"



def get_mapping():
    if not PMID_TO_PMC_MAPPING_PATH.exists():
        print('here')
        response = requests.get(PMID_TO_PMC_MAPPING_URL, stream=True)
        response.raise_for_status()
        with open(PMID_TO_PMC_MAPPING_PATH, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    df = pd.read_csv(PMID_TO_PMC_MAPPING_PATH)
    return {
        pmid: f"https://ftp.ncbi.nlm.nih.gov/pub/pmc/{file}"
        for pmid, file in zip(df["PMID"], df["File"])
    }, {pmid: pmc for pmid, pmc in zip(df["PMID"], df["Accession ID"])}


def download_pmc_content(pmid):
    pmid_download_mapping, pmid_pmc_mapping = get_mapping()

    with tempfile.TemporaryDirectory() as temp_dir:
        pmc_content_path = download_package_for_pmid(pmid, temp_dir, pmid_download_mapping)
        with tarfile.open(pmc_content_path, 'r:gz') as tar:
            tar.extractall(path=temp_dir)
        pmc = pmid_pmc_mapping[pmid]
        extracted_subdirectory = Path(temp_dir)/pmc


if __name__ == "__main__":
    download_pmc_content(32219006)
