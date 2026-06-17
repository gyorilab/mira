import logging
from typing import Tuple, Literal
from pathlib import Path

import pystow
from indra.literature.pubmed_client import (
    get_pmid_to_package_url_mapping,
    pmid_to_pmc_download_url,
)

from mira.sources.sympy_ode.extractors import (
    MineruExtractor,
    MarkerExtractor,
    XmlExtractor,
)
from mira.sources.sympy_ode.llm_util import (
    execute_template_model_from_sympy_odes,
)

from mira.openai_utility import OpenAIClient
from mira.metamodel import TemplateModel


ExtractionMethod = Literal["text", "image"]

logger = logging.getLogger(__name__)

BASE = pystow.module("mira", "paper_extraction")


def get_pmid_to_pmc_mapping_path() -> Path:
    return BASE.ensure(url=pmid_to_pmc_download_url)


def get_pmid_pmc_download_mapping():
    return get_pmid_to_package_url_mapping(
        get_pmid_to_pmc_mapping_path().as_posix()
    )


def get_template_model_from_pmid(pmid: str, extractor: str = "mineru",
                                 ode_extraction_method: ExtractionMethod = "text",
                                 pmid_to_download_mapping=None, client=None) \
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

    Returns
    -------
    :
        The template model extracted from the PubMed article
    :
        The pipeline result containing the extracted ODEs, corrected ODEs,
        grounded concepts and the path to the file used for extraction.
    """
    if client is None:
        client = OpenAIClient(model="gpt-5.4-mini", temperature=0.2)

    paper_base = BASE.join(pmid)

    pmc = Path(pmid_to_download_mapping[pmid]).name.removesuffix('.tar.gz')

    if extractor == "mineru":
        extractor_obj = MineruExtractor(pmid, pmc, paper_base,
                                        pmid_to_download_mapping,
                                        ode_extraction_method)
    elif extractor == "marker":
        extractor_obj = MarkerExtractor(pmid, pmc, paper_base,
                                        pmid_to_download_mapping,
                                        ode_extraction_method)
    elif extractor == "xml":
        extractor_obj = XmlExtractor(pmid, pmc)
    else:
        raise ValueError(f"Unknown extractor: {extractor}")

    ode = extractor_obj.extract(client=client)

    tm = execute_template_model_from_sympy_odes(ode_str=ode.final_ode_str,
                                                attempt_grounding=True,
                                                client=client)
    return tm, ode
