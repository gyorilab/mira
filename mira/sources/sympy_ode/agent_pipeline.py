import logging
from typing import Optional
import click

from mira.openai import OpenAIClient
from mira.sources.sympy_ode.agents import (
    ODEExtractionSpecialist,
    ConceptGrounder,
    ExecutionErrorCorrector,
)


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

    extractor = ODEExtractionSpecialist(client)
    result = extractor.process({"image_path": image_path})

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

    grounder = ConceptGrounder(client)
    result = grounder.process({"ode_str": ode_str})

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
    corrector = ExecutionErrorCorrector(client)
    result = corrector.process({"ode_str": ode_str})
    result = corrector.process({"ode_str": ode_str})

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
