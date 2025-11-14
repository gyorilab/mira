import json
import tempfile
import tarfile
import logging
from typing import Tuple, Literal
from pathlib import Path

import torch
import pystow
from indra.literature.pubmed_client import (
    download_package_for_pmid,
    get_pmid_to_package_url_mapping,
    pmid_to_pmc_download_url,
)
from mineru.cli.common import do_parse, read_fn

from mira.sources.sympy_ode.agent_pipeline import run_multi_agent_pipeline
from mira.sources.sympy_ode.llm_util import (
    execute_template_model_from_sympy_odes,
)
from mira.openai_utility import OpenAIClient
from mira.metamodel import TemplateModel

PMID_TO_PMC_MAPPING_PATH = pystow.ensure(
    "mira", "paper_extraction", url=pmid_to_pmc_download_url
)

ExtractionMethod = Literal["text", "image"]

logger = logging.getLogger(__name__)


def get_optimal_backend() -> str:
    """
    Automatically select backend based on available VRAM.
    Returns 'vlm-vllm-engine' for 8GB+, 'pipeline' otherwise. The vllm engine
    has higher accuracy and is faster. Check the "Local Deployment" section
    of the README.md here:
    https://github.com/opendatalab/MinerU/blob/master/README.md.
    """
    if not torch.cuda.is_available():
        logger.warning("CUDA not available, using pipeline backend with CPU")
        return "pipeline"

    # Get total VRAM in GB
    total_vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    logger.info(f"Detected {total_vram_gb:.2f} GB VRAM")

    if total_vram_gb >= 8.0:
        logger.info("Using VLM backend (faster, requires 8GB+ VRAM)")
        return "vlm-vllm-engine"
    else:
        logger.info(
            f"Using pipeline backend with CUDA (VLM requires 8GB+, you have {total_vram_gb:.2f}GB)"
        )
        return "pipeline"


def get_template_model_from_pmid(
    pmid: str, ode_extraction_method: ExtractionMethod = "text"
) -> Tuple[TemplateModel, str]:
    """
    Return a template model and the accompanying ODE string retrieved from a
    PubMed article representing an epidemiological model

    Parameters
    ----------
    pmid :
        The pmid of the article information is being retrieved for
    ode_extraction_method :
        The type of input that will be supplied to the LLM when extracting
        equations (i.e. text or images).

    Returns
    -------
    :
        The template model extracted from the PubMed article
    :
        The ODE string the template model is generated from
    """
    client = OpenAIClient()
    pmid_to_download_mapping = get_pmid_to_package_url_mapping(
        str(PMID_TO_PMC_MAPPING_PATH)
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        pmc_content_path = download_package_for_pmid(
            pmid, temp_dir, pmid_to_download_mapping
        )

        with tarfile.open(pmc_content_path, "r:gz") as tar:
            tar.extractall(path=temp_dir)

        pmc = pmid_to_download_mapping[pmid].split("/")[-1].split(".")[0]
        extracted_subdirectory = Path(temp_dir) / pmc

        try:
            nxml_file = list(extracted_subdirectory.glob("*.nxml"))[0]
        except IndexError:
            raise FileNotFoundError(
                f"No .nxml file found in {extracted_subdirectory}"
            )
        pdf_file = nxml_file.with_suffix(".pdf")
        if not pdf_file.exists():
            raise FileNotFoundError(
                f"No equivalent pdf file for downloaded .nxml file"
            )

        file_name_list = [pdf_file.stem]
        file_byte_list = [read_fn(pdf_file)]
        backend = get_optimal_backend()

        do_parse(
            output_dir=str(temp_dir),
            pdf_file_names=file_name_list,
            pdf_bytes_list=file_byte_list,
            p_lang_list=["en"],
            backend=backend,
            parse_method="auto",
            formula_enable=True,
            table_enable=False,
            f_draw_layout_bbox=False,
            f_draw_span_bbox=False,
            f_dump_md=True,
            f_dump_middle_json=False,
            f_dump_model_output=False,
            f_dump_orig_pdf=False,
            f_dump_content_list=True,
        )

        # Need filename without extension
        pdf_name = pdf_file.stem
        with open(
            f"{str(temp_dir)}/{pdf_name}/auto/{pdf_name}_content_list.json"
        ) as f:
            content_list = json.load(f)

        equation_content = [
            content
            for content in content_list
            if content.get("type") == "equation"
        ]

        markdown_text = "\n\n".join(
            [
                str((equation["text"], equation["text_format"]))
                for equation in equation_content
            ]
        )

        equation_img_paths = [
            str(
                Path(temp_dir)
                / f"{pdf_name}"
                / "auto"
                / f"{content['img_path']}"
            )
            for content in equation_content
        ]

        if ode_extraction_method == "text":
            ode_str, _ = run_multi_agent_pipeline(
                content_type="text", text_content=markdown_text
            )
        else:
            ode_str, _ = run_multi_agent_pipeline(
                content_type="image", image_path=equation_img_paths
            )

        tm = execute_template_model_from_sympy_odes(
            ode_str=ode_str, attempt_grounding=True, client=client
        )

        return tm, ode_str
