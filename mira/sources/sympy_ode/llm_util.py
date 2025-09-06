import base64
import re
from typing import Optional, List

from mira.metamodel import TemplateModel
from mira.openai import OpenAIClient, ImageFmts
from mira.sources.sympy_ode import template_model_from_sympy_odes
from mira.sources.sympy_ode.constants import (
    ODE_IMAGE_PROMPT,
    ODE_CONCEPTS_PROMPT_TEMPLATE,
    ERROR_CHECKING_PROMPT
)

ode_pattern = r"(odes\s*=\s*\[.*?\])\s*"
pattern = re.compile(ode_pattern, re.DOTALL)


class CodeExecutionError(Exception):
    """An error raised when there is an error executing the code"""


# Extraction of odes from image to str

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


# Error handling iteration: check and correct extracted odes (2-step)

def check_and_correct_extraction(
    ode_str: str,
    concept_data: Optional[dict],
    client: OpenAIClient,
    max_iterations: int = 3
) -> tuple[str, Optional[dict]]:
    """
    CORE VALIDATION: Takes ODEs + concepts, returns corrected versions.
    This is the actual validator that talks to the LLM.

    Role: Pure validation/correction logic - doesn't extract anything
    """
    import json

    current_code = ode_str
    current_concepts = concept_data

    for iteration in range(max_iterations):
        check_prompt = ERROR_CHECKING_PROMPT.replace(
            "{code}", current_code
        ).replace(
            "{concepts}", json.dumps(current_concepts, indent=2) if current_concepts is not None else "None"
        )

        response = client.run_chat_completion(check_prompt)

        raw_response = response.message.content
        print(f"Raw LLM response: {raw_response[:500]}...")  # Print first 500 chars for DEBUG

        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            if len(parts) > 1:
                cleaned = parts[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]

        try:
            result = json.loads(cleaned.strip())

            if not result.get("has_errors", False):
                print(f"Validation passed on iteration {iteration + 1}")
                break

            print(f"Iteration {iteration + 1}: Found errors: {result.get('errors', [])}")

            print(f"DEBUG: Response keys: {result.keys()}")
            if "corrected_code" in result:
                print(f"DEBUG: corrected_code exists, first 100 chars: {result['corrected_code'][:100]}")
            else:
                print("DEBUG: NO corrected_code in response!")

            if "corrected_code" in result:
                print(f"DEBUG: corrected_code field exists, length: {len(result['corrected_code'])}")
                print(f"DEBUG: First 200 chars of corrected_code: {result['corrected_code'][:200]}")
                current_code = result["corrected_code"]
            else:
                print("DEBUG: No corrected_code field in response!")

            if "corrected_concepts" in result:
                new_concepts = result.get("corrected_concepts")
                
                # Debug output
                print(f"DEBUG: Type of corrected_concepts: {type(new_concepts)}")
                if isinstance(new_concepts, dict):
                    print(f"DEBUG: Concepts has {len(new_concepts)} items")
                
                # Decision logic
                if new_concepts == "fixed concept_data if needed":
                    print("DEBUG: Skipping placeholder text")
                elif new_concepts == {} or new_concepts == "" or new_concepts is None:
                    print(f"DEBUG: Empty/None concepts returned, keeping current ({len(current_concepts) if current_concepts else 0} items)")
                elif isinstance(new_concepts, dict) and len(new_concepts) > 0:
                    print(f"DEBUG: Updating concepts with {len(new_concepts)} items")
                    current_concepts = new_concepts
                elif isinstance(new_concepts, str):
                    try:
                        exec(f"concept_data = {new_concepts}", globals(), locals())
                        extracted = locals().get("concept_data")
                        if extracted:
                            print(f"DEBUG: Extracted {len(extracted) if isinstance(extracted, dict) else 'non-dict'} concepts from string")
                            current_concepts = extracted
                    except Exception as e:
                        print(f"DEBUG: Failed to extract concepts from string: {e}")
                else:
                    print(f"DEBUG: Unexpected concepts type: {type(new_concepts)}, keeping current")
        except json.JSONDecodeError:
            print(f"Warning: Could not parse error checker response on iteration {iteration + 1}")
            continue

    if not current_concepts and concept_data:
        print("WARNING: Concepts became empty during correction, using original")
        current_concepts = concept_data

    return current_code, current_concepts



def validation_with_grounding(
    ode_str: str,
    client: OpenAIClient,
    attempt_grounding: bool = True,
    max_correction_iterations: int = 3,
) -> tuple[str, Optional[dict]]:
    """
    ORCHESTRATOR: Manages the full validation pipeline.
    1. Extracts concepts
    2. Calls check_and_correct_extraction for validation
    
    Role: Pipeline orchestration - coordinates extraction and validation
    """
    print("Running validation pipeline...")
    
    # Step 1: Extract concepts
    concept_data = None
    if attempt_grounding:
        try:
            concept_data = get_concepts_from_odes(ode_str, client)
            print(f"Extracted {len(concept_data) if concept_data else 0} concepts")
        except Exception as e:
            print(f"Warning: Concept extraction failed: {e}")
    
    # Step 2: Delegate to core validation function
    return check_and_correct_extraction(
        ode_str=ode_str,
        concept_data=concept_data,
        client=client,
        max_iterations=max_correction_iterations
    )


# TM
def execute_template_model_from_sympy_odes(
    checked_ode_str,
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
        exec(checked_ode_str, globals(), local_dict)
    except Exception as e:
        # Raise a CodeExecutionError to handle the error in the UI
        raise CodeExecutionError(f"Error while executing the code: {e}")
    # `odes` should now be defined in the local scope
    odes = local_dict.get("odes")
    assert odes is not None, "The code should define a variable called `odes`"
    if attempt_grounding:
        concept_data = get_concepts_from_odes(checked_ode_str, client)
    else:
        concept_data = None
    return template_model_from_sympy_odes(odes, concept_data=concept_data)