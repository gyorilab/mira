import logging
import textwrap
import click
from dataclasses import dataclass
from typing import Optional, Union, List, Dict

from mira.sources.sympy_ode import template_model_from_sympy_odes
from mira.metamodel import TemplateModel
from mira.openai_utility import OpenAIClient
from mira.sources.sympy_ode.llm_util import (
    image_file_to_odes_str,
    get_concepts_from_odes,
    clean_response,
    test_execution,
    pdf_file_to_odes_str,
    ContentType,
    test_ode_model,
    CodeExecutionError
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
    def final_ode_str(self) -> Optional[str]:
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
    except Exception as e:
        logger.info(f"  ERROR extracting ODEs: {e}")
        return ExtractionResult(status="failed", error=str(e))

    if ode_str == "odes = []":
        logger.info("  WARNING: No ODE string found in input")
        ode_str = None
    else:
        logger.info("ODEs extracted from input")
        logger.info(f"Length: {len(ode_str)} characters")

    return ExtractionResult(ode_str=ode_str)


# PHASE 2: CHECK AND CORRECT EXECUTION ERRORS
def fix_execution_errors(ode_str, client, error, max_attempts=10):
    """PHASE 2: Execution Error Correction

    Parameters
    ----------
    ode_str :
        The Sympy ODE string
    client :
        The OpenAI client
    error : 
        The error message from the failed execution attempt
    max_attempts :
        Maximum number of attempts to fix execution errors before giving up

    Returns
    -------
    :
        The ODE string free of execution errors
    """
    logger.info("PHASE 2: Execution Error Correction")

    for attempt in range(max_attempts):
        print(f"  Attempt {attempt + 1} to fix execution error {error}...")
        print(f"  Current ODE string : \n{ode_str} \n")
        prompt = textwrap.dedent(
            EXECUTION_ERROR_PROMPT.substitute(attempt=attempt + 1,
                                              max_attempts=max_attempts,
                                              ode_str=ode_str,
                                              error=error)
        ).strip()

        response = client.run_chat_completion(prompt)
        ode_str = clean_response(response.message.content)
        success, error = test_execution(ode_str)
        if success:
            return CorrectionResult(ode_str=ode_str, attempts=attempt + 1)

    # Failed after all attempts
    logger.info("  ERROR: Cannot fix execution errors - stopping")
    return CorrectionResult(status="failed", attempts=max_attempts,
                            error="Could not fix execution errors")


# PHASE 3: CONCEPT GROUNDING
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
    except Exception as e:
        logger.info(f"  ERROR grounding concepts: {e}")
        return GroundingResult(status="failed", error=str(e))

    if concepts:
        logger.info(f"  Extracted {len(concepts)} concepts")
    else:
        logger.info("  No concepts extracted")

    return GroundingResult(concepts=concepts)


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
        A PipelineResult with the extraction, correction and grounding results
    """

    if client is None:
        client = OpenAIClient()
    logger.info("-" * 60)
    logger.info("MULTI-AGENT ODE EXTRACTION & VALIDATION PIPELINE")
    logger.info("-" * 60)

    result = PipelineResult()

    # Phase 1: ODE Extraction from input
    result.extraction = extract_odes(image_path=image_path, client=client,
                                     content_type=content_type,
                                     text_content=text_content)
    if not result.extraction.success:
        logger.info("  ERROR in Phase 1 - stopping pipeline")
        return result
    
    if result.extraction.ode_str is None:
        logger.info("  No ODE string extracted in Phase 1 - stopping pipeline")
        return result

    # Phase 2: Execution error correction (only if the ODEs don't run as-is)
    success, error = test_execution(result.extraction.ode_str)
    if not success:
        result.correction = fix_execution_errors(result.extraction.ode_str,
                                                client, error)
        if not result.correction.success:
            logger.info("  ERROR in Phase 2 - stopping pipeline")
            return result

    # Phase 3: Concept Grounding
    result.grounding = concept_grounding(result.final_ode_str, client)

    logger.info("-" * 60)
    logger.info("PIPELINE COMPLETE")

    return result


def fix_mira_model_errors(ode_str, client, error, max_attempts=10):
    """PART 2: Fix MIRA OdeModel errors (e.g. missing derivative on LHS)
    
    Parameters
    ----------
    ode_str :
        The Sympy ODE string
    client :
        The OpenAI client
    error :
        The error message from the failed OdeModel test
    max_attempts :
        Maximum number of attempts to fix MIRA model errors before giving up
    
    Returns
    -------
    :
        The ODE string corrected to fix MIRA model errors, if successful. Otherwise 
        returns the original ODE string after max attempts.
    """
    logger.info("PART 2: MIRA Model Error Correction")
    for attempt in range(max_attempts):
        print(f"  Attempt {attempt + 1} to fix MIRA model error: {error}...")
        prompt = textwrap.dedent(
            EXECUTION_ERROR_PROMPT.substitute(
                attempt=attempt + 1,
                max_attempts=max_attempts,
                ode_str=ode_str,
                error=error
            )
        ).strip()

        response = client.run_chat_completion(prompt)
        ode_str = clean_response(response.message.content)

        exec_success, exec_error = test_execution(ode_str)
        if not exec_success:
            error = exec_error
            continue

        local_dict = {}
        exec(ode_str, {"__builtins__": __builtins__}, local_dict)
        odes = local_dict.get("odes")

        mira_success, error = test_ode_model(odes)
        if mira_success:
            return CorrectionResult(ode_str=ode_str, attempts=attempt + 1)
        
    return CorrectionResult(ode_str=ode_str, attempts=max_attempts)


def execute_template_model_from_sympy_odes(
    ode_str,
    attempt_grounding: bool,
    client: OpenAIClient,
) -> TemplateModel:
    """Create a TemplateModel from the sympy ODEs defined in the code snippet string

    Parameters
    ----------
    ode_str :
        The code snippet defining the ODEs
    attempt_grounding :
        Whether to attempt grounding the concepts in the ODEs. This will prompt the
        OpenAI chat completion to create concepts data to provide grounding for the
        concepts in the ODEs. The concepts data is then used to create the TemplateModel.
    client :
        The OpenAI client

    Returns
    -------
    :
        The TemplateModel created from the sympy ODEs.
    """
    if ode_str is None:
        logger.info("ODE string is None - cannot create TemplateModel")
        return None

    logger.info("Creating TemplateModel from Sympy ODEs...")

    # Part 1: Fix any SymPy execution errors
    success, error = test_execution(ode_str)
    if not success:
        result = fix_execution_errors(ode_str, client, error)
        ode_str = result.ode_str

    # Execute once with the (potentially corrected) string
    local_dict = locals()
    try:
        exec(ode_str, globals(), local_dict)
    except Exception as e:
        raise CodeExecutionError(f"Error while executing the code: {e}")

    odes = local_dict.get("odes")
    assert odes is not None, "The code should define a variable called `odes`"
    
    # Part 2: Fix any MIRA OdeModel errors
    success, error = test_ode_model(odes)
    if not success:
        result = fix_mira_model_errors(ode_str, client, error)
        # Re-execute and rebuild after correction
        local_dict = locals()
        exec(result.ode_str, globals(), local_dict)
        odes = local_dict.get("odes")
        assert test_ode_model(odes)[0], "MIRA OdeModel error correction failed"

    if attempt_grounding:
        concept_data = get_concepts_from_odes(ode_str, client)
    else:
        concept_data = None
    
    return template_model_from_sympy_odes(odes, concept_data=concept_data)


@click.command()
@click.argument("image_path", type=click.Path(exists=True))
@click.option("--content-type", default="image",
              help="Type of the input content ('image' or 'pdf')")
def main(image_path, content_type="image"):
    """
    Run Multi-agent pipeline for ODE extraction and validation from CLI from an
    image or pdf file.
    """
    run_multi_agent_pipeline(image_path=image_path, content_type=content_type)


if __name__ == "__main__":
    main()
