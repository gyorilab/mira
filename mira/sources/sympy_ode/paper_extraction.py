import tempfile
import tarfile
from typing import Dict, Tuple
from pathlib import Path

import pandas as pd
import requests
from indra.literature.pubmed_client import download_package_for_pmid
from mineru.cli.common import do_parse, read_fn

from mira.sources.sympy_ode.agent_pipeline import run_multi_agent_pipeline
from mira.sources.sympy_ode.llm_util import (
    execute_template_model_from_sympy_odes,
)
from mira.openai import OpenAIClient
from mira.metamodel import TemplateModel


HERE = Path(__file__).parent.resolve()
PMID_TO_PMC_MAPPING_URL = (
    "https://ftp.ncbi.nlm.nih.gov/pub/pmc/oa_file_list.csv"
)
PMID_TO_PMC_MAPPING_PATH = HERE / "pmid_pmc_mapping.csv"


def get_mappings() -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    Helper method to retrieve pmid to pmc download links and pmid to pmc mappings

    Returns
    -------
    :
        Dictionary mapping PMID strings to PMC download URLs
    :
        Dictionary mapping PMID strings to PMC accession IDs
    """
    if not PMID_TO_PMC_MAPPING_PATH.exists():
        response = requests.get(PMID_TO_PMC_MAPPING_URL, stream=True)
        response.raise_for_status()
        with open(PMID_TO_PMC_MAPPING_PATH, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    df = pd.read_csv(PMID_TO_PMC_MAPPING_PATH)
    return {
        str(int(pmid)): f"https://ftp.ncbi.nlm.nih.gov/pub/pmc/{file}"
        for pmid, file in zip(df["PMID"], df["File"])
        if pd.notna(pmid)
    }, {
        str(int(pmid)): pmc
        for pmid, pmc in zip(df["PMID"], df["Accession ID"])
        if pd.notna(pmid)
    }


def get_template_model_from_pmid(pmid: str) -> Tuple[TemplateModel, str]:
    """
    Return a template model and the accompanying ODE string retrieved from a
    PubMed article representing an epidemiological model

    Parameters
    ----------
    pmid :
        The pmid of the article information is being retrieved for

    Returns
    -------
    :
        The template model extracted from the PubMed article
    :
        The ODE string the template model is generated from
    """
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
        # # Add error handling if these files aren't available
        nxml_file = list(extracted_subdirectory.glob("*.nxml"))[0]
        pdf_file = nxml_file.with_suffix(".pdf")

        file_name_list = [pdf_file.stem]
        file_byte_list = [read_fn(pdf_file)]
        do_parse(
            output_dir=str(temp_dir),
            pdf_file_names=file_name_list,
            pdf_bytes_list=file_byte_list,
            p_lang_list=["en"],
            backend="pipeline",
            parse_method="txt",
            formula_enable=True,
            table_enable=False,
            f_draw_layout_bbox=False,
            f_draw_span_bbox=False,
            f_dump_md=True,
            f_dump_middle_json=False,
            f_dump_model_output=False,
            f_dump_orig_pdf=False,
            f_dump_content_list=False,
        )

        pdf_name = pdf_file.stem  # filename without extension
        md_path = Path(temp_dir) / pdf_name / "txt" / f"{pdf_name}.md"

        with open(md_path, "r", encoding="utf-8") as f:
            markdown = f.read()

        ode_str, _ = run_multi_agent_pipeline(
            content_type="text", text_content=markdown
        )

        tm = execute_template_model_from_sympy_odes(
            ode_str=ode_str, attempt_grounding=True, client=client
        )

        return tm, ode_str
