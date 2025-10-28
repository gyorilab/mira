import logging
import textwrap
from typing import Optional

import click

from mira.openai import OpenAIClient
from mira.sources.sympy_ode.llm_util import (
    image_file_to_odes_str,
    get_concepts_from_odes,
    clean_response,
    test_execution
)
from mira.sources.sympy_ode.constants import EXECUTION_ERROR_PROMPT


logger = logging.getLogger(__name__)


# PHASE 1: ODE EXTRACTION
def extract_odes(
    image_path: str,
    client: OpenAIClient,
) -> str:
    """Phase 1: Extract ODEs from image using ODEExtractionSpecialist

    Parameters
    ----------
    image_path :
        Path to the image containing ODEs
    client :
        OpenAI client

    Returns
    -------
    :
        The Sympy ODE string
    """
    logger.info("PHASE 1: ODE Extraction from Image")

    try:
        ode_str = image_file_to_odes_str(image_path, client)
        status = 'complete'
    except Exception as e:
        ode_str = ''
        status = f'failed: {str(e)}'

    result = {
        'ode_str': ode_str,
        'phase': 'extraction',
        'status': status
    }

    logger.info("ODEs extracted from image")
    logger.info(f"Length: {len(result['ode_str'])} characters")

    return result["ode_str"]


def concept_grounding(
    ode_str: str,
    client: OpenAIClient,
) -> Optional[dict]:
    """Phase 2: Extract concepts from ODE string using ConceptGrounder

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
    logger.info("PHASE 2: Concept Grounding")


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

    concepts = result.get("concepts")

    if concepts:
        logger.info(f"  Extracted {len(concepts)} concepts")
    else:
        logger.info("  No concepts extracted")

    return concepts


# PHASE 3: CHECK AND CORRECT EXECUTION ERRORS
def fix_execution_errors(ode_str, client):
    """PHASE 3: Execution Error Correction

    Parameters
    ----------
    ode_str :
        The Sympy ODE string
    client :
        The OpenAI client

    Returns
    -------
    :
        The ODE string free of execution errors
    """

    max_attempts = 3

    for attempt in range(max_attempts):
        if test_execution(ode_str):
            return {
                'ode_str': ode_str,
                'execution_report': {'executable': True, 'attempts': attempt},
                'phase': 'execution_correction',
                'status': 'complete'
            }

        prompt = textwrap.dedent(
            EXECUTION_ERROR_PROMPT.substitute(attempt=attempt + 1,
                                              max_attempts=max_attempts,
                                              ode_str=ode_str)
        ).strip()

        response = client.run_chat_completion(prompt)
        ode_str = clean_response(response.message.content)

    # Failed after all attempts
    if not test_execution(ode_str):
        result = {
            'ode_str': '',
            'execution_report': {'executable': False, 'fatal': True},
            'phase': 'execution_correction',
            'status': 'FAILED'
        }
    else:
        result = {
            'ode_str': ode_str,
            'execution_report': {'executable': True, 'attempts': max_attempts},
            'phase': 'execution_correction',
            'status': 'complete'
        }

    if result["status"] == "FAILED":
        logger.info("  ERROR: Cannot fix execution errors - stopping")
        raise RuntimeError("Phase 3 failed - cannot continue with broken code")

    if result["execution_report"].get("errors_fixed"):
        logger.info("Fixed execution errors")
    else:
        logger.info("No execution errors found")

    return result["ode_str"]


def run_multi_agent_pipeline(
    image_path: str,
    client: OpenAIClient = None,
    biomodel_name: str = None,
) -> tuple[str, Optional[dict], dict]:
    """Return Multi-agent pipeline for ODE extraction and validation

    Phase 1: Extract ODEs from image
    Phase 2: Extract concepts (grounding)
    Phase 3: Handle execution errors

    Parameters
    ----------
    image_path :
        Path to the image containing ODEs
    client :
        OpenAI client
    biomodel_name :
        Name of the biomodel for ground truth comparison

    Returns
    -------
    :
        Validated ODE string, concepts, and evaluation metrics
    """

    if client is None:
        client = OpenAIClient()
    logger.info("-" * 60)
    logger.info("MULTI-AGENT ODE EXTRACTION & VALIDATION PIPELINE")
    if biomodel_name:
        logger.info(f"Biomodel: {biomodel_name}")
    logger.info("-" * 60)

    # Phase 1: ODE Extraction from image
    ode_str = extract_odes(image_path, client)

    # Phase 2: Concept Grounding
    concepts = concept_grounding(ode_str, client)

    # Phase 3: Execution error correction
    ode_str = fix_execution_errors(ode_str, client)

    logger.info("-" * 60)
    logger.info("PIPELINE COMPLETE")

    return ode_str, concepts


@click.command()
@click.argument("image_path", type=click.Path(exists=True))
@click.option("--biomodel-name", default=None, help="Name of the biomodel")
def main(image_path: str, biomodel_name: str = None):
    """Run Multi-agent pipeline for ODE extraction and validation from CLI"""
    run_multi_agent_pipeline(image_path=image_path, biomodel_name=biomodel_name)


if __name__ == "__main__":
    main()
