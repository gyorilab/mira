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
   current_code = ode_str
   current_concepts = concept_data
   
   for iteration in range(max_iterations):
       check_prompt = ERROR_CHECKING_PROMPT.replace(
           "{code}", current_code
       )

       response = client.run_chat_completion(check_prompt)

       raw_response = response.message.content
       print(f"Raw LLM response: {raw_response[:500]}...")  # Print first 500 chars for DEBUG

       cleaned = clean_response(raw_response)
       
       # The LLM now returns just the corrected SymPy code, not JSON
       if cleaned and cleaned.strip():
           print(f"Iteration {iteration + 1}: Received corrected code")
           current_code = cleaned.strip()
           
           # Try to validate the corrected code by attempting to execute it
           try:
               import sympy
               from sympy import Symbol, Function, Eq, Derivative
               
               local_dict = {
                   'sympy': sympy,
                   'Symbol': Symbol,
                   'Function': Function,
                   'Eq': Eq,
                   'Derivative': Derivative
               }
               
               exec(current_code, globals(), local_dict)
               odes = local_dict.get("odes")
               
               if odes is not None:
                   print(f"Validation passed on iteration {iteration + 1}")
                   break
               else:
                   print(f"Iteration {iteration + 1}: Code executed but 'odes' not found")
                   
           except Exception as e:
               print(f"Iteration {iteration + 1}: Code execution failed: {e}")
               # Continue to next iteration if there are still errors
       else:
           print(f"Iteration {iteration + 1}: Empty or invalid response")
           continue
   
   if not current_concepts and concept_data:
    print("WARNING: Concepts became empty during correction, using original")
    current_concepts = concept_data

   return current_code, current_concepts


def validate_and_correct_odes(
    ode_str: str,
    client: OpenAIClient,
    max_correction_iterations: int = 3
) -> str:
    """STEP 2: Error checking and correcting iteration for extracted SymPy strings
    
    Parameters
    ----------
    ode_str :
        The extracted SymPy ODE string
    client :
        The OpenAI client
    max_correction_iterations :
        Maximum number of correction attempts
        
    Returns
    -------
    str
        The checked and corrected ODE string in the exact same SymPy format
    """
    print("Running error checking and correction...")
    
    # Run error checking and correction (no concept extraction needed here)
    corrected_ode_str, _ = check_and_correct_extraction(
        ode_str=ode_str,
        concept_data=None,  # No concepts needed for this step
        client=client,
        max_iterations=max_correction_iterations
    )

    # Ensure the output is in valid SymPy format (as code)
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
        exec(corrected_ode_str, globals(), local_dict)
        odes = local_dict.get("odes")
        if odes is None:
            raise ValueError("Corrected code does not define 'odes'")
        # Convert odes to sympy code string
        from sympy.printing.pycode import pycode
        if isinstance(odes, list):
            odes_code = "[\n" + ",\n".join(pycode(eq) for eq in odes) + "\n]"
        else:
            odes_code = pycode(odes)
        # Reconstruct the code string in sympy format
        sympy_code = (
            "from sympy import Symbol, Function, Eq, Derivative\n"
            "t = Symbol('t')\n"
            "x = Function('x')(t)\n"
            "y = Function('y')(t)\n"
            f"odes = {odes_code}\n"
        )
        return sympy_code
    except Exception as e:
        print(f"Warning: Could not parse corrected ODE string to sympy format: {e}")
        # Fallback: return the corrected string as is
        return corrected_ode_str


def execute_template_model_from_sympy_odes(
    ode_str,
    client: OpenAIClient,
    concept_data: Optional[dict] = None,
) -> TemplateModel:
    """STEP 3: Create a TemplateModel from the corrected sympy ODEs

    Parameters
    ----------
    ode_str :
        The corrected ODE code string
    client :
        The OpenAI client
    concept_data :
        Optional concept data dictionary (can be added later if needed)

    Returns
    -------
    :
        The TemplateModel created from the sympy ODEs.
    """
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
        exec(ode_str, globals(), local_dict)
    except Exception as e:
        # Raise a CodeExecutionError to handle the error in the UI
        raise CodeExecutionError(f"Error while executing the code: {e}")
    
    # `odes` should now be defined in the local scope
    odes = local_dict.get("odes")
    assert odes is not None, "The code should define a variable called `odes`"

    # Ensure concept_data is either a dict or None
    if concept_data is not None and not isinstance(concept_data, dict):
        print(f"Warning: concept_data is {type(concept_data)}, converting to empty dict")
        concept_data = {}

    return template_model_from_sympy_odes(odes, concept_data=concept_data)


def extract_and_validate_odes(
    image_path: str,
    client: OpenAIClient,
    max_correction_iterations: int = 3
) -> TemplateModel:
    """Complete three-step pipeline: extract, validate/correct, then execute
    
    Parameters
    ----------
    image_path :
        Path to the image file
    client :
        The OpenAI client
    max_correction_iterations :
        Maximum correction attempts
        
    Returns
    -------
    :
        The validated TemplateModel
    """
    print(f"Starting three-step extraction from {image_path}")
    
    # STEP 1: Extract SymPy string from image
    print("Step 1: Extracting SymPy string from image...")
    ode_str = image_file_to_odes_str(image_path, client)
    
    # STEP 2: Error checking and correcting iteration
    print("Step 2: Error checking and correcting...")
    corrected_ode_str = validate_and_correct_odes(
        ode_str=ode_str,
        client=client,
        max_correction_iterations=max_correction_iterations
    )
    
    # STEP 3: Execute template model from corrected SymPy
    print("Step 3: Executing template model...")
    template_model = execute_template_model_from_sympy_odes(
        ode_str=corrected_ode_str,
        client=client,
        concept_data=None  # No concepts in this pipeline
    )
    
    print("Three-step extraction complete")
    return template_model