import logging
import pystow

from typing import List, Literal, Optional, Tuple

from indra.literature.pmc_client import id_lookup

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
    PipelineResult,
    execute_template_model_from_sympy_odes,
)

from mira.openai_utility import OpenAIClient
from mira.metamodel import Scenario, TemplateModel


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


def get_template_model_from_pmid(pmid: str, extractor: str = "mineru",
                                 ode_extraction_method: ExtractionMethod = "text",
                                 client=None, parameter_only=False) \
        -> Tuple[Optional[TemplateModel], Optional[PipelineResult],
                 List[Scenario]]:
    """
    Return a template model, the ODE extraction result and parameter
    scenarios retrieved from a PubMed article representing an epidemiological
    model

    Parameters
    ----------
    pmid :
        The pmid of the article information is being retrieved for
    extractor :
        The method used to extract the ODEs from the article.
    ode_extraction_method :
        The type of input that will be supplied to the LLM when extracting
        equations (i.e. text or images).
    client :
        An instance of the OpenAIClient to use for LLM interactions. If None,
        a default client will be created.
    parameter_only :
        If True, only extract parameters and not the full template model.

    Returns
    -------
    :
        The template model extracted from the PubMed article, None if
        ``parameter_only`` is True.
    :
        The pipeline result containing the extracted ODEs, corrected ODEs,
        grounded concepts and the path to the file used for extraction, None
        if ``parameter_only`` is True.
    :
        The parameter scenarios extracted from the article's tables.
    """
    if client is None:
        client = OpenAIClient(model="us.openai.gpt-6-luna", bedrock=True)

    paper_base = BASE.join(pmid)

    pmc = id_lookup(pmid, 'pmid').get('pmcid')
    if not pmc:
        raise ValueError(f"PMID {pmid} has no PMCID.")

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
