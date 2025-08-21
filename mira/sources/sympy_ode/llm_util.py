import base64
import re
from typing import Optional, List

from mira.metamodel import TemplateModel
from mira.openai import OpenAIClient, ImageFmts
from mira.sources.sympy_ode import template_model_from_sympy_odes
from mira.sources.sympy_ode.constants import (
    ODE_IMAGE_PROMPT,
    ODE_CONCEPTS_PROMPT_TEMPLATE
)

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


def check_and_correct_extraction(
    ode_str: str,
    concept_data: Optional[dict],
    client: OpenAIClient,
    max_iterations: int = 3
) -> tuple[str, Optional[dict]]:
    """Check extracted ODEs and concepts for errors and correct them
    
    Parameters
    ----------
    ode_str :
        The extracted ODE code string
    concept_data :
        The extracted concept data dictionary
    client :
        The OpenAI client
    max_iterations :
        Maximum number of correction attempts
        
    Returns
    -------
    tuple[str, Optional[dict]]
        Corrected ODE string and concept data
    """
    import json
    
    current_code = ode_str
    current_concepts = concept_data
    
    for iteration in range(max_iterations):
        # Prepare checking prompt
        check_prompt = ERROR_CHECKING_PROMPT.format(
            code=current_code,
            concepts=json.dumps(current_concepts, indent=2) if current_concepts else "None"
        )
        
        # Get error check response
        response = client.run_chat_completion(check_prompt)
        
        try:
            # Parse JSON response
            result = json.loads(clean_response(response.message.content))
            
            if not result.get("has_errors", False):
                # No errors found, return current version
                print(f"Validation passed on iteration {iteration + 1}")
                break
            
            # Apply corrections
            print(f"Iteration {iteration + 1}: Found errors: {result.get('errors', [])}")
            
            if "corrected_code" in result:
                current_code = result["corrected_code"]
            
            if "corrected_concepts" in result and result["corrected_concepts"] != "fixed concept_data if needed":
                # Parse the corrected concepts if it's a string
                if isinstance(result["corrected_concepts"], str):
                    try:
                        # Try to extract concept_data from the string
                        exec(f"concept_data = {result['corrected_concepts']}", globals(), locals())
                        current_concepts = locals().get("concept_data", current_concepts)
                    except:
                        current_concepts = result["corrected_concepts"]
                else:
                    current_concepts = result["corrected_concepts"]
                    
        except json.JSONDecodeError:
            print(f"Warning: Could not parse error checker response on iteration {iteration + 1}")
            break
    
    return current_code, current_concepts



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

    if use_multi_agent:
            # First agent: Original extraction (already done, we have ode_str)
            
            # Get concepts if requested
            concept_data = None
            if attempt_grounding:
                try:
                    concept_data = get_concepts_from_odes(ode_str, client)
                except Exception as e:
                    print(f"Warning: Concept extraction failed: {e}")
                    concept_data = None
            
            # Second agent: Check and correct
            print("Running multi-agent validation...")
            corrected_ode_str, corrected_concepts = check_and_correct_extraction(
                ode_str, 
                concept_data, 
                client
            )
            
            # Use corrected versions
            ode_str = corrected_ode_str
            concept_data = corrected_concepts
    else:
        # Original single-agent logic
        if attempt_grounding:
            concept_data = get_concepts_from_odes(ode_str, client)
        else:
            concept_data = None

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
