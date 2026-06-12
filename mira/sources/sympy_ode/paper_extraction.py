import json
import tarfile
import logging
from typing import Tuple, Literal
from pathlib import Path
import torch
import gc
from bs4 import BeautifulSoup
import re

import pystow
from indra.literature.pubmed_client import (
    download_package_for_pmid,
    get_pmid_to_package_url_mapping,
    pmid_to_pmc_download_url,
)
from indra.literature.pmc_client import _get_s3_artifact
from mineru.cli.common import do_parse, read_fn

from mira.sources.sympy_ode.agent_pipeline import run_multi_agent_pipeline
from mira.sources.sympy_ode.llm_util import (
    execute_template_model_from_sympy_odes,
)
from mira.openai_utility import OpenAIClient
from mira.metamodel import TemplateModel

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import save_output


ExtractionMethod = Literal["text", "image"]

logger = logging.getLogger(__name__)

BASE = pystow.module("mira", "paper_extraction")


def get_optimal_backend() -> str:
    """
    Automatically select backend based on available VRAM.
    Returns 'vlm-vllm-engine' for 8GB+, 'pipeline' otherwise. The vllm engine
    has higher accuracy and is faster.
    Check the "Local Deployment" section of the README.md here:
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
            f"Using pipeline backend with CUDA (VLM requires 8GB+, you have "
            f"{total_vram_gb:.2f}GB)"
        )
        return "pipeline"


def get_pmid_to_pmc_mapping_path() -> Path:
    return BASE.ensure(url=pmid_to_pmc_download_url)


def run_mineru_pipeline(pdf_file, paper_base: Path,
                        ode_extraction_method : str = "text") -> dict:
    """
    Run the MinerU pipeline to extract equations from the given PDF file,
    then run the multi-agent pipeline to extract the ODE string from the equations.
    
    Parameters
    ----------
    pdf_file :
        The path to the PDF file
    paper_base :
        The base directory for the paper
    ode_extraction_method :
        The method to use for ODE extraction ("text" or "image")    
        Default is "text", sends the equations in text format to the LLM.
    
    Returns
    -------
    :
        A dictionary containing the ODE string, corrected ODE string, grounded
        concepts and the path to the file used for extraction.
    """

    # Need filename without extension
    pdf_name = pdf_file.stem
    content_list = None
    content_list_file = None

    def find_parse_method_path(paper_base: Path, pdf_name: str) -> Path:
        vlm_path = paper_base / pdf_name / "vlm"
        if vlm_path.exists():
            return vlm_path
        auto_path = paper_base / pdf_name / "auto"
        if auto_path.exists():
            return auto_path
        raise FileNotFoundError(
            f"No parse method directory found for {pdf_name} in {paper_base}"
        )
    
    try:
        parse_method_path = find_parse_method_path(paper_base, pdf_name)
        content_list_file = parse_method_path / f"{pdf_name}_content_list.json"
    except FileNotFoundError:
        logger.warning(f"No parse method directory found for {pdf_name} in "
                       f"{paper_base}, running MinerU pipeline")

    # If the content list file already exists, skip running the MinerU
    # pipeline and just load the content list
    if content_list_file:
        file_path = Path(content_list_file)
        if file_path.is_file():
            with open(file_path) as f:
                logger.info(f"Found existing content list file at "
                            f"{content_list_file}, loading content list from file")
                content_list = json.load(f)
    else:
        file_name_list = [pdf_file.stem]
        file_byte_list = [read_fn(pdf_file)]
        backend = get_optimal_backend()
        do_parse(
            output_dir=paper_base.as_posix(),
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
        parse_method_path = find_parse_method_path(paper_base, pdf_name)
        content_list_file = parse_method_path / f"{pdf_name}_content_list.json"

        with open(content_list_file) as f:
            content_list = json.load(f)

    equation_content = [content for content in content_list
                        if content.get("type") == "equation"]

    # If we use image mode we need to require that the image
    # paths exist for the given equations
    if ode_extraction_method == "image":
        equation_content = [content for content in equation_content
                            if content.get("img_path")]

    markdown_text = "\n\n".join(
        [
            str((equation["text"], equation["text_format"]))
            for equation in equation_content
        ]
    )

    equation_img_paths = [
        (parse_method_path / equation['img_path']).as_posix()
        for equation in equation_content
    ]

    if ode_extraction_method == "text":
        ode = run_multi_agent_pipeline(content_type="text",
                                       text_content=markdown_text)
    else:
        ode = run_multi_agent_pipeline(content_type="image",
                                       image_path=equation_img_paths)

    ode["extraction_file"] = str(Path(content_list_file))
        
    return ode


def run_marker_pipeline(pdf_file, pmid: str, paper_base: Path,
                        ode_extraction_method : str = "text") -> dict:
    """
    Run the Marker pipeline to extract equations from the given PDF file,
    then run the multi-agent pipeline to extract the ODE string from the
    equations.
    
    Parameters
    ----------
    pdf_file :
        The path to the PDF file
    pmid:
        PMID of the paper 
    paper_base :
        The base directory for the paper
    ode_extraction_method :
        The method to use for ODE extraction   
        Currently only "text" is supported, the equations are sent in text
        format to the LLM.
    
    Returns
    -------
    :
        A dictionary containing the ODE string, corrected ODE string, grounded
        concepts and the path to the file used for extraction.
    """

    # Need filename without extension
    pdf_name = pdf_file.stem

    out_dir = paper_base / "marker"
    html_file = out_dir / f"{pmid}.html"
    out_dir.mkdir(parents=True, exist_ok=True)

    file_path = Path(html_file)

    # If the html file already exists, skip running the Marker pipeline and
    # just load the content list
    if file_path.is_file():
        with open(html_file) as f:
            soup = BeautifulSoup(f.read(), "html.parser")

    else:
        models = create_model_dict()
        converter = PdfConverter(
            artifact_dict=models,
            renderer="marker.renderers.html.HTMLRenderer"
        )
        rendered = converter(str(pdf_file))
        save_output(rendered, out_dir, fname_base=pmid)
        
        try:
            del converter
            del models
            del rendered
        except NameError:
            pass
        gc.collect()

        with open(html_file) as f:
            soup = BeautifulSoup(f.read(), "html.parser")

    block_equations = soup.find_all("math", display="block")
    block_latex = [eq.get_text(strip=True) for eq in block_equations]

    equation_text = [(eq, "latex") for eq in block_latex]

    if ode_extraction_method == "text":
        ode = run_multi_agent_pipeline(content_type="text",
                                       text_content=equation_text)

    ode["extraction_file"] = str(html_file)
        
    return ode


def run_xml_pipeline(pmc, pmid: str) -> dict:
    """
    Run the XML pipeline to extract equations using the PMC ID, then run the
    multi-agent pipeline to extract the ODE string from the equations.
    
    Parameters
    ----------
    pmc :
        The PMC ID of the paper
    pmid:
        PMID of the paper 
    
    Returns
    -------
    :
        A dictionary containing the ODE string, corrected ODE string and
        grounded concepts.
    """
    logger.info("running xml")
    try:
        eqns = []
        resp = _get_s3_artifact(pmc, "xml") 
        xml_data = resp.text
        soup = BeautifulSoup(xml_data, 'lxml-xml')

        tex_blocks = soup.find_all('tex-math')
        eq_type = "latex"
        if len(tex_blocks) > 0:
            for block in tex_blocks:
                raw = block.get_text()
                # Extract just the math content between \begin{document} and \end{document}
                match = re.search(r'\\begin\{document\}(.*?)\\end\{document\}',
                                  raw, re.DOTALL)
                if match:
                    latex = match.group(1).strip()
                    eqns.append(latex)
        else:
            math_blocks = soup.find_all('disp-formula')
            eq_type = "text"
            for block in math_blocks:
                eqns.append(block.get_text())
        
        markdown_text = "\n\n".join(
                    [
                        str((equation, eq_type))
                        for equation in eqns
                    ]
                )
            
        ode = run_multi_agent_pipeline(content_type="text",
                                       text_content=markdown_text)

        ode["extraction_file"] = "No intermediate created"
    except Exception as e:
        logger.warning(f"Failed to extract model for PMID {pmid}: {e}")

    return ode


def get_template_model_from_pmid(pmid: str, extractor:str = "mineru",
                                 ode_extraction_method: ExtractionMethod = "text",
                                 pmid_to_download_mapping=None) -> Tuple[TemplateModel, str]:
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
    pmid_to_download_mapping :
        A dictionary mapping pmids to their corresponding download paths.

    Returns
    -------
    :
        The template model extracted from the PubMed article
    :
        A dictonary containing the ODE string, corrected ODE string, grounded
        concepts and the path to the file used for extraction.
    """
    client = OpenAIClient()

    paper_base = BASE.join(pmid)

    pmc = Path(pmid_to_download_mapping[pmid]).name.rstrip('.tar.gz')

    if extractor == "xml":
        ode = run_xml_pipeline(pmc=pmc, pmid=pmid)

    extracted_subdirectory = paper_base / pmc
    nxml_files = list(extracted_subdirectory.glob("*.nxml"))

    if not nxml_files:
        pmc_content_path = download_package_for_pmid(
            pmid, paper_base, pmid_to_download_mapping
        )

        with tarfile.open(pmc_content_path, "r:gz") as tar:
            tar.extractall(path=paper_base)

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
    
    logger.info(f"Extracted subdirectory: {extracted_subdirectory}")

    if extractor == "mineru":
        ode = run_mineru_pipeline(pdf_file=pdf_file, paper_base=paper_base,
                                  ode_extraction_method=ode_extraction_method)

    elif extractor == "marker":
        ode = run_marker_pipeline(pdf_file=pdf_file, paper_base=paper_base,
                                  ode_extraction_method=ode_extraction_method,
                                  pmid=pmid)
    
    tm = execute_template_model_from_sympy_odes(ode_str=ode["corrected_ode_str"],
                                                attempt_grounding=True,
                                                client=client)
    return tm, ode
