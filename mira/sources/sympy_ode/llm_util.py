import base64
import re
from typing import Optional, List

from mira.metamodel import TemplateModel
from mira.openai import OpenAIClient, ImageFmts
from mira.sources.sympy_ode import template_model_from_sympy_odes
from mira.sources.sympy_ode.constants import (
    ODE_IMAGE_PROMPT,
    ODE_CONCEPTS_PROMPT_TEMPLATE,
    ERROR_CHECK__AND_CORRECT_PROMPT
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

def test_code_execution(code: str) -> tuple[bool, str]:
    """
    Test if the code can be executed without errors.
    
    Returns:
        (success: bool, error_message: str)
    """
    import sympy
    from sympy import Symbol, Function, Eq, Derivative
    
    local_dict = {
        'sympy': sympy,
        'Symbol': Symbol,
        'Function': Function,
        'Eq': Eq,
        'Derivative': Derivative
    }
    
    try:
        exec(code, globals(), local_dict)
        odes = local_dict.get("odes")
        if odes is None:
            return False, "Code executed but 'odes' variable not defined"
        return True, "Code executed successfully"
    except Exception as e:
        return False, f"Execution error: {str(e)}"


def check_and_correct_extraction(
    ode_str: str,
    concept_data: Optional[dict],
    client: OpenAIClient,
    max_iterations: int = 3
) -> tuple[str, Optional[dict]]:
    """
    CORE VALIDATION: Takes ODEs + concepts, returns corrected versions.
    Implements the 3-iteration approach from the prompt:
    - Iteration 1: Fix execution-blocking errors
    - Iteration 2: Fix mathematical accuracy errors  
    - Iteration 3: Fix parameter definition issues
    
    Each iteration tests the corrected code with exec() to verify fixes work.
    """
    import json

    current_code = ode_str
    current_concepts = concept_data
    
    # Test initial code
    success, error_msg = test_code_execution(current_code)
    print(f"Initial code test: {'PASS' if success else 'FAIL'} - {error_msg}")

    for iteration in range(max_iterations):
        print(f"\n ITERATION {iteration + 1}")
        
        # Create iteration-specific prompt
        iteration_prompt = ERROR_CHECK__AND_CORRECT_PROMPT.replace(
            "{code}", current_code
        ).replace(
            "{concepts}", json.dumps(current_concepts, indent=2) if current_concepts is not None else "None"
        )
        
        # Add iteration-specific instructions
        if iteration == 0:
            iteration_prompt += "\n\nFOCUS: Fix only execution-blocking errors (imports, undefined variables, syntax errors)."
        elif iteration == 1:
            iteration_prompt += "\n\nFOCUS: Fix mathematical accuracy errors - especially check for: parameter name mismatches (beta vs Beta), arithmetic operation confusion (* vs +), missing terms, time dependency issues."
        elif iteration == 2:
            iteration_prompt += "\n\nFOCUS: Fix parameter definition issues and concept grounding."

        response = client.run_chat_completion(iteration_prompt)
        raw_response = response.message.content
        print(f"Raw LLM response: {raw_response[:500]}...")

        # Clean and parse response
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            parts = cleaned.split("```")
            if len(parts) > 1:
                cleaned = parts[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]

        try:
            result = json.loads(cleaned.strip())
            
            # Check if we have corrected code
            if "corrected_code" in result and result["corrected_code"]:
                new_code = result["corrected_code"]
                print(f"Got corrected code from LLM")
                
                # Test the corrected code
                success, error_msg = test_code_execution(new_code)
                print(f"Corrected code test: {'PASS' if success else 'FAIL'} - {error_msg}")
                
                if success:
                    # Code executes successfully, update current_code
                    current_code = new_code
                    print(f"Updated code with corrected version")
                else:
                    print(f"Corrected code still has execution errors, keeping current code")
            else:
                print("No corrected_code in LLM response")

            # Handle concepts
            if "corrected_concepts" in result:
                new_concepts = result.get("corrected_concepts")
                
                if new_concepts == "fixed concept_data if needed":
                    print("DEBUG: Skipping placeholder text")
                elif new_concepts == {} or new_concepts == "" or new_concepts is None:
                    print(f"DEBUG: Empty/None concepts returned, keeping current")
                elif isinstance(new_concepts, dict) and len(new_concepts) > 0:
                    print(f"DEBUG: Updating concepts with {len(new_concepts)} items")
                    current_concepts = new_concepts
                elif isinstance(new_concepts, str):
                    try:
                        exec(f"concept_data = {new_concepts}", globals(), locals())
                        extracted = locals().get("concept_data")
                        if extracted:
                            print(f"DEBUG: Extracted concepts from string")
                            current_concepts = extracted
                    except Exception as e:
                        print(f"DEBUG: Failed to extract concepts from string: {e}")

            # Check if we should continue iterating
            if not result.get("has_errors", False):
                print(f"LLM reports no errors on iteration {iteration + 1}")
                # Still test the code to be sure
                success, error_msg = test_code_execution(current_code)
                if success:
                    print(f"Validation passed on iteration {iteration + 1}")
                    break
                else:
                    print(f"LLM says no errors but code still fails: {error_msg}")
            else:
                print(f"Iteration {iteration + 1}: Found errors: {result.get('errors', {})}")

        except json.JSONDecodeError as e:
            print(f"Warning: Could not parse error checker response on iteration {iteration + 1}: {e}")
            continue

    # Final test
    success, error_msg = test_code_execution(current_code)
    print(f"\nFinal code test: {'PASS' if success else 'FAIL'} - {error_msg}")
    
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
    """
    print("Running validation pipeline...")
    
    concept_data = None
    if attempt_grounding:
        try:
            concept_data = get_concepts_from_odes(ode_str, client)
            print(f"Extracted {len(concept_data) if concept_data else 0} concepts")
        except Exception as e:
            print(f"Warning: Concept extraction failed: {e}")
    
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
    concept_data: Optional[dict] = None,
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
    from sympy import Symbol, Function, Eq, Derivative
    odes: List[sympy.Eq] = None
    # Execute the code and expose the `odes` variable to the local scope
    local_dict = {
        'sympy': sympy,
        'Symbol': Symbol,
        'Function': Function,
        'Eq': Eq,
        'Derivative': Derivative
    }
    try:
        exec(checked_ode_str, globals(), local_dict)
    except Exception as e:
        # Raise a CodeExecutionError to handle the error in the UI
        raise CodeExecutionError(f"Error while executing the code: {e}")
    # `odes` should now be defined in the local scope
    odes = local_dict.get("odes")
    assert odes is not None, "The code should define a variable called `odes`"
    if attempt_grounding and concept_data is None:
        concept_data = get_concepts_from_odes(checked_ode_str, client)
    elif not attempt_grounding:
        concept_data = None
    return template_model_from_sympy_odes(odes, concept_data=concept_data)