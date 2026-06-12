import logging
import textwrap
import click
from dataclasses import dataclass
from typing import Optional, Union, List, Dict

from mira.openai_utility import OpenAIClient
from mira.sources.sympy_ode.llm_util import (
    image_file_to_odes_str,
    get_concepts_from_odes,
    clean_response,
    test_execution,
    pdf_file_to_odes_str,
    ContentType
)
from mira.sources.sympy_ode.constants import (EXECUTION_ERROR_PROMPT,
                                              ODE_MARKDOWN_PROMPT)
from mira.metamodel import Concept


logger = logging.getLogger(__name__)


@dataclass
class PhaseResult:
    """Base result for a single pipeline phase.

    Attributes
    ----------
    status :
        Either "complete" or "failed".
    error :
        Error message if the phase failed, otherwise None.
    """
    status: str = "complete"
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.status == "complete"


@dataclass
class ExtractionResult(PhaseResult):
    """Result of Phase 1, ODE extraction from the input."""
    ode_str: Optional[str] = None


@dataclass
class CorrectionResult(PhaseResult):
    """Result of Phase 2, execution error correction.

    Attributes
    ----------
    attempts :
        Number of correction attempts made.
    """
    ode_str: Optional[str] = None
    attempts: int = 0


@dataclass
class GroundingResult(PhaseResult):
    """Result of Phase 3, concept grounding."""
    concepts: Optional[Dict[str, Concept]] = None


@dataclass
class PipelineResult:
    """Aggregate result of the multi-agent ODE extraction pipeline.

    Attributes
    ----------
    extraction :
        Result of Phase 1 (ODE extraction).
    correction :
        Result of Phase 2 (execution error correction), if run.
    grounding :
        Result of Phase 3 (concept grounding), if run.
    extraction_file :
        Path to the intermediate file used for extraction, if any.
    """
    extraction: Optional[ExtractionResult] = None
    correction: Optional[CorrectionResult] = None
    grounding: Optional[GroundingResult] = None
    extraction_file: Optional[str] = None

    @property
    def best_ode_str(self) -> Optional[str]:
        """Return the best available ODE string.

        Prefers the corrected ODE string if Phase 2 succeeded, otherwise
        falls back to the extracted ODE string.
        """
        if self.correction is not None and self.correction.success:
            return self.correction.ode_str
        if self.extraction is not None and self.extraction.success:
            return self.extraction.ode_str
        return None


# PHASE 1: ODE EXTRACTION
def extract_odes(
    client: OpenAIClient,
    content_type: ContentType,
    image_path: Union[List[str],str] = None,
    text_content: str = None
):
    """Phase 1: Extract ODEs from input

    Parameters
    ----------
    client :
        OpenAI client
    content_type :
        What type of format is the input
    image_path :
        Path to the image file(s) containing ODEs
    text_content :
        The Markdown text containing th ODEs

    Returns
    -------
    :
        The Sympy ODE string
    """
    logger.info("PHASE 1: ODE Extraction from input")

    try:
        if content_type == "image":
            ode_str = image_file_to_odes_str(image_path, client)
        elif content_type == "pdf":
            ode_str = pdf_file_to_odes_str(image_path, client)
        elif content_type == "text":
            ode_str = clean_response(client.run_chat_completion_with_text(ODE_MARKDOWN_PROMPT, text_content))
        status = 'complete'
    except Exception as e:
        ode_str = ''
        status = f'failed: {str(e)}'

    result = {
        'ode_str': ode_str,
        'phase': 'extraction',
        'status': status
    }

    logger.info("ODEs extracted from input")
    logger.info(f"Length: {len(result['ode_str'])} characters")

    return result


def concept_grounding(ode_str: str, client: OpenAIClient):
    """Phase 3: Extract concepts from the ODE string

    Parameters
    ----------
    ode_str :
        The Sympy ODE string
    client :
        The OpenAI client

    Returns
    -------
    :
        The mapping of concept symbol to grounded Concept
    """
    logger.info("PHASE 3: Concept Grounding")

    try:
        concepts = get_concepts_from_odes(ode_str, client)
        status = 'complete'
    except Exception as e:
        concepts = None
        status = f'failed: {str(e)}'

    result = {
        'concepts': concepts,
        'phase': 'concept_grounding',
        'status': status
    }

    if concepts:
        logger.info(f"  Extracted {len(concepts)} concepts")
    else:
        logger.info("  No concepts extracted")

    return result


# PHASE 2: CHECK AND CORRECT EXECUTION ERRORS
def fix_execution_errors(ode_str, client, max_attempts=10):
    """PHASE 2: Execution Error Correction

    Parameters
    ----------
    ode_str :
        The Sympy ODE string
    client :
        The OpenAI client
    max_attempts :
        Maximum number of attempts to fix execution errors before giving up

    Returns
    -------
    :
        The ODE string free of execution errors
    """
    for attempt in range(max_attempts):
        prompt = textwrap.dedent(
            EXECUTION_ERROR_PROMPT.substitute(attempt=attempt + 1,
                                              max_attempts=max_attempts,
                                              ode_str=ode_str)
        ).strip()

        response = client.run_chat_completion(prompt)
        ode_str = clean_response(response.message.content)
        if test_execution(ode_str):
            return {
                'ode_str': ode_str,
                'attempts': attempt + 1,
                'phase': 'execution_correction',
                'status': 'complete'
            }


    # Failed after all attempts
    logger.info("  ERROR: Cannot fix execution errors - stopping")
    return {
        'ode_str': '',
        'attempts': max_attempts,
        'phase': 'execution_correction',
        'status': 'failed'
    }


def run_multi_agent_pipeline(
    content_type: ContentType,
    text_content: str = None,
    image_path: Union[str,List[str]] = None,
    client: OpenAIClient = None,
):
    """Return Multi-agent pipeline for ODE extraction and validation

    Phase 1: Extract ODEs from input
    Phase 2: Handle execution errors
    Phase 3: Extract concepts (grounding)

    Parameters
    ----------
    content_type :
        What type of format is the content
    text_content :
        The PubMed article text containing ODEs
    image_path :
        Path to the file containing ODEs
    client :
        OpenAI client

    Returns
    -------
    :
        Dictionary containing extracted ODE string, corrected ODE string, and grounded concepts
    """

    if client is None:
        client = OpenAIClient()
    logger.info("-" * 60)
    logger.info("MULTI-AGENT ODE EXTRACTION & VALIDATION PIPELINE")
    logger.info("-" * 60)

    result = {}
    try:
        # Phase 1: ODE Extraction from image
        result['ode_extraction'] = \
            extract_odes(image_path=image_path, client=client,
                         content_type=content_type,
                         text_content=text_content)
    except Exception as e:
        logger.info(f"  ERROR in Phase 1: {str(e)} - stopping pipeline")
        result['ode_extraction'] = None
        return result

    if not test_execution(result['ode_extraction']['ode_str']):
        try:
            # Phase 2: Execution error correction
            result['correcrted_ode'] = \
                fix_execution_errors(result['ode_extraction']['ode_str'],
                                     client)
        except Exception as e:
            logger.info(f"  ERROR in Phase 2: {str(e)} - stopping pipeline")
            result['corrected_ode'] = None
            return result

    if result['corrected_ode']['status'] != 'complete':
        return result

    best_ode = result.get('corrected_ode', result['ode_extraction'])

    try:
        # Phase 3: Concept Grounding
        concept_result = concept_grounding(best_ode['ode_str'], client)
    except Exception as e:
        logger.info(f"  ERROR in Phase 3: {str(e)} - stopping pipeline")
        concept_result = None
    result["concept"] = concept_result

    logger.info("-" * 60)
    logger.info("PIPELINE COMPLETE")

    return result


@click.command()
@click.argument("image_path", type=click.Path(exists=True))
@click.option("--biomodel-name", default=None, help="Name of the biomodel")
def main(image_path: str, biomodel_name: str = None):
    """
    Run Multi-agent pipeline for ODE extraction and validation from CLI from an
    image or pdf file.
    """
    run_multi_agent_pipeline(image_path=image_path, biomodel_name=biomodel_name)


if __name__ == "__main__":
    main()
