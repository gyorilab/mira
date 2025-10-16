import base64
import re
import logging
from typing import Optional, List

from mira.metamodel import TemplateModel
from mira.openai import OpenAIClient, ImageFmts
from mira.sources.sympy_ode import template_model_from_sympy_odes
from mira.sources.sympy_ode.constants import (
    ODE_IMAGE_PROMPT,
    ODE_CONCEPTS_PROMPT_TEMPLATE,
    EXECUTION_ERROR_PROMPT
)

logger = logging.getLogger(__name__)

ode_pattern = r"(odes\s*=\s*\[.*?\])\s*"
pattern = re.compile(ode_pattern, re.DOTALL)


class CodeExecutionError(Exception):
    """An error raised when there is an error executing the code"""


def image_file_to_odes_str(
    image_path: str,
    client: OpenAIClient,
) -> str:
    """Get an ODE string from an image file depicting an ODE system

    Parameters
    ----------
    image_path :
        The path to the image file
    client :
        A :class:`mira.openai.OpenAIClient` instance

    Returns
    -------
    :
        The ODE string extracted from the image. The string should contain the code
        necessary to define the ODEs using sympy.
    """
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_format = image_path.split(".")[-1]
    return image_to_odes_str(image_bytes, client, image_format)

def image_to_odes_str(
    image_bytes: bytes,
    client: OpenAIClient,
    image_format: ImageFmts = "png"
) -> str:
    """Get an ODE string from an image depicting an ODE system

    Parameters
    ----------
    image_bytes :
        The bytes of the image
    client :
        The OpenAI client
    image_format :
        The format of the image. The default is "png".

    Returns
    -------
    :
        The ODE string extracted from the image. The string should contain the code
        necessary to define the ODEs using sympy.
    """
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    response = extract_ode_str_from_base64_image(base64_image=base64_image, 
                                                 image_format=image_format,
                                                 client=client)
    return response


def clean_response(response: str) -> str:
    """Clean up the response from the OpenAI chat completion

    Parameters
    ----------
    response :
        The response from the OpenAI chat completion.

    Returns
    -------
    :
        The cleaned up response. The response is stripped of the code block
        markdown, i.e. the triple backticks and the language specifier. It is also
        stripped of leading and trailing whitespaces.
    """
    response = response.replace("```python", "")
    response = response.replace("```", "")
    return response.strip()


def extract_ode_str_from_base64_image(
    base64_image: str,
    image_format: ImageFmts,
    client: OpenAIClient,
    prompt: str = None
):
    """Get the ODE string from an image in base64 format

    Parameters
    ----------
    base64_image :
        The base64 encoded image
    image_format :
        The format of the image
    client :
        The OpenAI client
    prompt :
        The prompt to send to the OpenAI chat completion. If None, the default
        prompt is used (see :data:`mira.sources.sympy_ode.constants.ODE_IMAGE_PROMPT`)

    Returns
    -------
    :
        The ODE string extracted from the image. The string should contain the code
        necessary to define the ODEs using sympy.
    """
    if prompt is None:
        prompt = ODE_IMAGE_PROMPT

    choice = client.run_chat_completion_with_image(
        message=prompt,
        base64_image=base64_image,
        image_format=image_format,
    )
    text_response = clean_response(choice.message.content)
    return text_response


def get_concepts_from_odes(
    ode_str: str,
    client: OpenAIClient,
) -> Optional[dict]:
    """Get the concepts data from the ODEs defined in the code snippet

    Parameters
    ----------
    ode_str :
        The string containing the code snippet defining the ODEs
    client :
        The openAI client

    Returns
    -------
    :
        The concepts data in the form of a dictionary, or None if no concepts data
        could be generated.
    """
    # Cut out the part of the code that defines the `odes` variable
    # Regular expression to capture the `odes` variable assignment and definition
    match = re.search(pattern, ode_str)

    if match:
        odes_code = match.group(1)
    else:
        raise ValueError("No code snippet defining the variable `odes` found")

    # Prompt the OpenAI chat completion to create the concepts data dictionary
    prompt = ODE_CONCEPTS_PROMPT_TEMPLATE.substitute(ode_insert=odes_code)
    response = client.run_chat_completion(prompt)

    # Clean up the response
    response_text = clean_response(response.message.content)
    

    # Extract the concepts from the response using exec
    locals_dict = locals()
    exec(response_text, globals(), locals_dict)
    concept_data = locals_dict.get("concept_data")
    assert concept_data is not None, "The code should define a variable called `concept_data`"
    return concept_data


def run_multi_agent_pipeline(
    image_path: str,
    client: OpenAIClient,
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
    logger.info("-"*60)
    logger.info("MULTI-AGENT ODE EXTRACTION & VALIDATION PIPELINE")
    if biomodel_name:
        logger.info(f"Biomodel: {biomodel_name}")
    logger.info("-"*60)
    
    # Phase 1: ODE Extraction from image
    ode_str = extract_odes(image_path, client)
    
    # Phase 2: Concept Grounding
    concepts = concept_grounding(ode_str, client)
    
    # Phase 3: Execution error correction
    ode_str = fix_execution_errors(ode_str, client)
    
    logger.info("-"*60)
    logger.info("PIPELINE COMPLETE")

    return ode_str, concepts


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
    
    from mira.sources.sympy_ode.agents import ODEExtractionSpecialist
    extractor = ODEExtractionSpecialist(client)
    result = extractor.process({'image_path': image_path})
    
    logger.info("ODEs extracted from image")
    logger.info(f"Length: {len(result['ode_str'])} characters")
    
    return result['ode_str']


# PHASE 2: CONCEPT GROUNDING
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
    
    from mira.sources.sympy_ode.agents import ConceptGrounder
    grounder = ConceptGrounder(client)
    result = grounder.process({'ode_str': ode_str})
    
    concepts = result.get('concepts')
    
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
    
    from mira.sources.sympy_ode.agents import ExecutionErrorCorrector
    corrector = ExecutionErrorCorrector(client)
    result = corrector.process({'ode_str': ode_str})
    
    if result['status'] == 'FAILED':
        logger.info("  ERROR: Cannot fix execution errors - stopping")
        raise RuntimeError("Phase 3 failed - cannot continue with broken code")
    
    if result['execution_report'].get('errors_fixed'):
        logger.info("Fixed execution errors")
    else:
        logger.info("No execution errors found")
    
    return result['ode_str']


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
    # FixMe, for now use `exec` on the code, but need to find a safer way to execute
    #  the code
    # Import sympy just in case the code snippet does not import it
    import sympy
    odes: List[sympy.Eq] = None
    # Execute the code and expose the `odes` variable to the local scope
    local_dict = locals()
    try:
        exec(ode_str, globals(), local_dict)
    except Exception as e:
        # Raise a CodeExecutionError to handle the error in the UI
        raise CodeExecutionError(f"Error while executing the code: {e}")
    # `odes` should now be defined in the local scope
    odes = local_dict.get("odes")
    assert odes is not None, "The code should define a variable called `odes`"
    if attempt_grounding:
        concept_data = get_concepts_from_odes(ode_str, client)
    else:
        concept_data = None
    return template_model_from_sympy_odes(odes, concept_data=concept_data)