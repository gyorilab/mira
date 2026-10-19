import logging
import pystow
import requests

from typing import Tuple, Literal

from mira.sources.sympy_ode.extractors import (
    MineruExtractor,
    MarkerExtractor,
    XmlExtractor,
    Pix2TextExtractor,
    DoclingExtractor,
    ChandraExtractor,
    PaddleOCRExtractor,
    LlamaParseExtractor,
    ReductoExtractor,
    GlmOcrExtractor,
    NougatExtractor,
    GlmOcrHfExtractor
)
from mira.sources.sympy_ode.agent_pipeline import (
    execute_template_model_from_sympy_odes,
)

from mira.openai_utility import OpenAIClient
from mira.metamodel import TemplateModel


ExtractionMethod = Literal["text", "image"]

logger = logging.getLogger(__name__)

BASE = pystow.module("mira", "paper_extraction")

EXTRACTORS = {
    'marker': MarkerExtractor,
    'mineru': MineruExtractor,
    'pix2text': Pix2TextExtractor,
    'docling': DoclingExtractor,
    'chandra': ChandraExtractor,
    'paddleocr': PaddleOCRExtractor,
    'llamaparse': LlamaParseExtractor,
    'reducto': ReductoExtractor,
    'glmocr': GlmOcrExtractor,
    'nougat': NougatExtractor,
    'glmocr_hf': GlmOcrHfExtractor
}

PMC_IDCONV_URL = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"

def pmid_to_pmcid(pmid: str) -> str:
    res = requests.get(
        PMC_IDCONV_URL,
        params={"ids": pmid, "format": "json", "tool": "mira",
                "email": "you@example.com"},
    )
    res.raise_for_status()
    pmcid = res.json()["records"][0].get("pmcid")
    if not pmcid:
        raise ValueError(f"PMID {pmid} has no PMCID.")
    return pmcid


def get_template_model_from_pmid(pmid: str, extractor: str = "mineru",
                                 ode_extraction_method: ExtractionMethod = "text",
                                 pmid_to_download_mapping=None, client=None,
                                 parameter_only=False) \
        -> Tuple[TemplateModel, str]:
    """
    Return a template model and the accompanying ODE string retrieved from a
    PubMed article representing an epidemiological model

    Parameters
    ----------
    pmid :
        The pmid of the article information is being retrieved for
    extractor :
        The method used to extract the ODEs from the article.
    ode_extraction_method :
        The type of input that will be supplied to the LLM when extracting
        equations (i.e. text or images).
    pmid_to_download_mapping :
        A dictionary mapping pmids to their corresponding download paths.
    client :
        An instance of the OpenAIClient to use for LLM interactions. If None,
        a default client will be created.
    parameter_only :
        If True, only extract parameters and not the full template model.

    Returns
    -------
    :
        The template model extracted from the PubMed article
    :
        The pipeline result containing the extracted ODEs, corrected ODEs,
        grounded concepts and the path to the file used for extraction.
    """
    if client is None:
        client = OpenAIClient(model="us.openai.gpt-6-luna",
                               max_completion_tokens=32768)

    paper_base = BASE.join(pmid)

    pmc = pmid_to_pmcid(pmid)

    if extractor != 'xml' and extractor not in EXTRACTORS:
        raise ValueError(f"Unknown extractor: {extractor}")

    # Tables are always read from the PMC XML, whichever extractor is used
    # for the equations, since the XML keeps the table structure intact.
    xml_extractor = XmlExtractor(pmid, pmc)

    if parameter_only:
        tm, ode = None, None
        scenarios = xml_extractor.extract_parameters(client=client)
    else:
        if extractor == 'xml':
            extractor_obj = xml_extractor
        else:
            extractor_obj = EXTRACTORS[extractor](pmid, pmc, paper_base,
                                                  pmid_to_download_mapping,
                                                  ode_extraction_method)
        ode = extractor_obj.extract(client=client)
        del extractor_obj
        tm = execute_template_model_from_sympy_odes(ode=ode,
                                                    attempt_grounding=True,
                                                    client=client)
        scenarios = xml_extractor.extract_parameters(client=client,
                                                     template_model=tm)

    del xml_extractor
    return tm, ode, scenarios
