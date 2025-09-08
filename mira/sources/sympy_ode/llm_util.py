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


def image_file_to_odes_str(     #reads the image input files
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


def image_to_odes_str(      #converting to base64
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


def extract_ode_str_from_base64_image(      #from image to str
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


def get_concepts_from_odes(         #uses the template for grounding
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
       check_prompt = ERROR_CHECKING_PROMPT.replace(
           "{code}", current_code
       ).replace(
           "{concepts}", json.dumps(current_concepts, indent=2) if current_concepts is not None else "None"
       )

       response = client.run_chat_completion(check_prompt)

       raw_response = response.message.content
       #print(f"Raw LLM response: {raw_response[:500]}...")  # Print first 500 chars for DEBUG

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

           print(f"Response keys: {result.keys()}")
           if "corrected_code" in result:
               print(f"corrected_code exists")
           else:
               print("NO corrected_code in response!")
           
           if "corrected_code" in result:
               print(f"corrected_code field exists, length: {len(result['corrected_code'])}")
               current_code = result["corrected_code"]
           else:
               print("No corrected_code field in response!")
           
           if "corrected_concepts" in result and result["corrected_concepts"] != "fixed concept_data if needed":
            print(f"Type of corrected_concepts from JSON: {type(result['corrected_concepts'])}")
            print(f"Content: {result['corrected_concepts'][:200] if isinstance(result['corrected_concepts'], str) else result['corrected_concepts']}")
    
            if isinstance(result["corrected_concepts"], str):
                try:
                    exec(f"concept_data = {result['corrected_concepts']}", globals(), locals())
                    current_concepts = locals().get("concept_data", current_concepts)
                except:
                    current_concepts = result["corrected_concepts"]
            else:
                   current_concepts = result["corrected_concepts"]
                   
       except json.JSONDecodeError:
           print(f"Warning: Could not parse error checker response on iteration {iteration + 1}")
           continue
   
   if not current_concepts and concept_data:
    print("WARNING: Concepts became empty during correction, using original")
    current_concepts = concept_data
    
   if current_concepts is None or (isinstance(current_concepts, dict) and len(current_concepts) == 0):
       print("WARNING: Concepts became empty during correction, using original")
       current_concepts = concept_data

   return current_code, current_concepts


def execute_template_model_from_sympy_odes(
    ode_str,
    attempt_grounding: bool,
    client: OpenAIClient,
    use_multi_agent: bool = True,
    max_correction_iterations: int = 3,
    return_corrected: bool = False, 
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

    return_corrected : bool
        If True, return tuple of (template_model, corrected_ode_str, corrected_concepts)
        If False, return only template_model (backward compatible)

    Returns
    -------
    :
        The TemplateModel created from the sympy ODEs, or tuple if return_corrected=True
    """
    corrected_ode_str = None
    corrected_concepts = None
    
    if use_multi_agent:
        # Get concepts first
        concept_data = None
        if attempt_grounding:
            try:
                concept_data = get_concepts_from_odes(ode_str, client)
            except Exception as e:
                print(f"Warning: Concept extraction failed: {e}")
                concept_data = None
        
        # Run multi-agent validation
        print("Running multi-agent validation...")
        corrected_ode_str, corrected_concepts = check_and_correct_extraction(
            ode_str, 
            concept_data, 
            client,
            max_iterations=max_correction_iterations
        )
    else:
        corrected_ode_str = ode_str
        if attempt_grounding:
            corrected_concepts = get_concepts_from_odes(ode_str, client)
        else:
            corrected_concepts = None
    
    # Execute the corrected (or original) code
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
        exec(corrected_ode_str, globals(), local_dict)  # USE corrected_ode_str directly
    except Exception as e:
        raise CodeExecutionError(f"Error while executing the code: {e}")
    
    odes = local_dict.get("odes")
    assert odes is not None, "The code should define a variable called `odes`"
    
    # Ensure concepts are valid
    if corrected_concepts is not None and not isinstance(corrected_concepts, dict):
        print(f"Warning: corrected_concepts is {type(corrected_concepts)}, converting to empty dict")
        corrected_concepts = {}
    
    # Create template model with corrected versions
    template_model = template_model_from_sympy_odes(odes, concept_data=corrected_concepts)
    
    if return_corrected:
        return template_model, corrected_ode_str, corrected_concepts
    else:
        return template_model


def extract_and_validate_odes(
    image_path: str,
    client: OpenAIClient,
    attempt_grounding: bool = True,
    max_correction_iterations: int = 3
) -> TemplateModel:
    """Complete multi-agent pipeline: extract, validate, and correct ODEs from image
    
    Parameters
    ----------
    image_path :
        Path to the image file
    client :
        The OpenAI client
    attempt_grounding :
        Whether to ground concepts
    max_correction_iterations :
        Maximum correction attempts
        
    Returns
    -------
    :
        The validated Model
    """
    print(f"Starting multi-agent extraction from {image_path}")
    
    print("Agent 1: Extracting ODEs from image...")
    ode_str = image_file_to_odes_str(image_path, client)
    
    print("Agent 2: Validating and correcting...")
    template_model = execute_template_model_from_sympy_odes(
        ode_str=ode_str,
        attempt_grounding=attempt_grounding,
        client=client,
        use_multi_agent=True,
        max_correction_iterations=max_correction_iterations
    )
    
    print("Multi-agent extraction complete")
    return template_model