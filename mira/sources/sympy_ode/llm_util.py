import base64
import re
import json
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
    response = hierarchical_extraction(base64_image, image_format, client)
    
    return response

def hierarchical_extraction(base64_image: str, image_format: str, client: OpenAIClient) -> str:
    """Three-stage hierarchical extraction for better parameter resolution"""
    
    # Extract equation structure
    structure = extract_equation_structure(base64_image, image_format, client)
    
    # Extract and analyze parameters with context
    parameters = extract_parameters_with_context(base64_image, image_format, structure, client)
    
    # Combine and resolve ambiguities
    final_odes_str = combine_structure_and_parameters(structure, parameters, base64_image, image_format, client)
    
    return final_odes_str


def extract_equation_structure(base64_image: str, image_format: str, client: OpenAIClient) -> dict:
    """Extract the equation structure from the image"""
    prompt = """Extract the STRUCTURE of the differential equations from this image.
    
    Focus on:
    1. What compartments exist (S, E, I, R, etc.)
    2. What flows between compartments
    3. What mathematical operations are used (+, -, *, /)
    4. What terms are missing or unclear
    
    Return as JSON:
    {
        "compartments": ["S", "E", "I", "R"],
        "flows": [
            {"from": "S", "to": "E", "type": "infection", "terms": ["beta*S*I/N"]},
            {"from": "E", "to": "I", "type": "progression", "terms": ["kappa*E"]}
        ],
        "missing_terms": ["recovery terms", "death terms"],
        "unclear_parameters": ["kappa_1 vs kappa*rho1", "delta_i vs delta_1"]
    }
    """
    
    response = client.run_chat_completion_with_image(
        message=prompt,
        base64_image=base64_image,
        image_format=image_format
    )
    
    try:
        return json.loads(clean_response(response.message.content))
    except:
        return {"compartments": [], "flows": [], "missing_terms": [], "unclear_parameters": []}

def extract_parameters_with_context(base64_image: str, image_format: str, structure: dict, client: OpenAIClient) -> dict:
    """Extract the parameters with context from the image"""
    prompt = f"""Extract PARAMETERS from this image, focusing on parameter variants and compound parameters.

    STRUCTURE CONTEXT: {json.dumps(structure, indent=2)}
    
    CRITICAL: Look for:
    1. **Parameter variants**: kappa_1, kappa_2 vs kappa*rho1, kappa*rho2
    2. **Compound parameters**: beta*S*I/N (not beta_S_I_N)
    3. **Subscript patterns**: delta_i, delta_p (not delta_1, delta_2)
    4. **Missing parameters**: N for population normalization
    
    Return as JSON:
    {{
        "base_parameters": ["beta", "kappa", "gamma", "delta"],
        "parameter_variants": {{
            "kappa": ["kappa*rho1", "kappa*rho2", "kappa*(1-rho1-rho2)"],
            "delta": ["delta_i", "delta_p", "delta_h"]
        }},
        "compound_forms": {{
            "kappa_1": "kappa*rho1",
            "kappa_2": "kappa*rho2"
        }},
        "population_parameters": ["N"],
        "unclear_parameters": ["kappa_1 vs kappa*rho1", "delta_1 vs delta_i"]
    }}
    """
    
    response = client.run_chat_completion_with_image(
        message=prompt,
        base64_image=base64_image,
        image_format=image_format
    )
    
    try:
        return json.loads(clean_response(response.message.content))
    except:
        return {"base_parameters": [], "parameter_variants": {}, "compound_forms": {}, "population_parameters": [], "unclear_parameters": []}

def combine_structure_and_parameters(structure: dict, parameters: dict, base64_image: str, image_format: str, client: OpenAIClient) -> str:
    """Combine the structure and parameters into final SymPy equations"""
    prompt = f"""Combine this structure and parameters into complete SymPy equations.

    STRUCTURE: {json.dumps(structure, indent=2)}
    PARAMETERS: {json.dumps(parameters, indent=2)}
    
    CRITICAL RULES:
    1. Use compound forms: kappa*rho1 NOT kappa_1
    2. Preserve descriptive subscripts: delta_i NOT delta_1
    3. Include population normalization: /N where needed
    4. Maintain mathematical structure: addition vs multiplication
    
    Generate complete SymPy code with:
    - All imports
    - Parameter definitions
    - Complete ODE equations
    - Proper variable naming
    """
    
    response = client.run_chat_completion(prompt)
    return clean_response(response.message.content)


def validate_parameter_extraction(ode_str: str, parameters: dict) -> dict:
    """General parameter validation for any parameter types"""
    import re
    
    validation_results = {
        "parameter_errors": [],
        "suggestions": [],
        "patterns_found": []
    }
    
    # Find all parameter patterns in the code
    # Look for common patterns: base_param_variant, base_param*sub_param, etc.
    param_patterns = re.findall(r'\b([a-zA-Z]+)_([a-zA-Z0-9]+)\b', ode_str)
    compound_patterns = re.findall(r'\b([a-zA-Z]+)\*([a-zA-Z0-9]+)\b', ode_str)
    
    # Check for numbered subscripts that should be descriptive
    numbered_subscripts = re.findall(r'\b([a-zA-Z]+)_(\d+)\b', ode_str)
    
    for base_param, variant in numbered_subscripts:
        # Check if this should be a compound parameter
        if f"{base_param}*{variant}" not in ode_str:
            validation_results["parameter_errors"].append(
                f"Parameter {base_param}_{variant} might be {base_param}*{variant}"
            )
            validation_results["suggestions"].append(
                f"Consider if {base_param}_{variant} should be {base_param}*{variant}"
            )
    
    # Check for missing population normalization in transmission terms
    transmission_terms = re.findall(r'\b([a-zA-Z]+)\*([A-Z])\(t\)\*([A-Z])\(t\)', ode_str)
    for param, comp1, comp2 in transmission_terms:
        if "/N" not in ode_str:
            validation_results["parameter_errors"].append(
                f"Transmission term {param}*{comp1}(t)*{comp2}(t) missing population normalization /N"
            )
            validation_results["suggestions"].append(
                f"Add N = Symbol('N') and use {param}*{comp1}(t)*{comp2}(t)/N"
            )
    
    # Check for inconsistent parameter naming patterns
    all_params = re.findall(r'\b([a-zA-Z]+(?:_[a-zA-Z0-9]+)?)\b', ode_str)
    param_counts = {}
    for param in all_params:
        if param not in ['t', 'S', 'E', 'I', 'R', 'P', 'A', 'H', 'F', 'N']:  # Exclude common variables
            param_counts[param] = param_counts.get(param, 0) + 1
    
    # Find parameters used only once (potential typos)
    for param, count in param_counts.items():
        if count == 1 and len(param) > 2:  # Short names might be intentional
            validation_results["patterns_found"].append(
                f"Parameter {param} used only once - check for typos"
            )
    
    # Check for missing parameter definitions
    defined_params = re.findall(r'([a-zA-Z]+)\s*=\s*Symbol', ode_str)
    used_params = set(re.findall(r'\b([a-zA-Z]+(?:_[a-zA-Z0-9]+)?)\b', ode_str))
    used_params -= {'t', 'S', 'E', 'I', 'R', 'P', 'A', 'H', 'F', 'N', 'sympy', 'Symbol', 'Function', 'Eq', 'Derivative'}
    
    missing_definitions = used_params - set(defined_params)
    if missing_definitions:
        validation_results["parameter_errors"].append(
            f"Missing parameter definitions: {list(missing_definitions)}"
        )
        validation_results["suggestions"].append(
            f"Define missing parameters: {', '.join(missing_definitions)} = Symbol('{', '.join(missing_definitions)}')"
        )
    
    return validation_results



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
           
           if "corrected_concepts" in result and result["corrected_concepts"] != "fixed concept_data if needed":
            print(f"DEBUG: Type of corrected_concepts from JSON: {type(result['corrected_concepts'])}")
            print(f"DEBUG: Content: {result['corrected_concepts'][:200] if isinstance(result['corrected_concepts'], str) else result['corrected_concepts']}")
    
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

   return current_code, current_concepts



def execute_template_model_from_sympy_odes(
    ode_str,
    attempt_grounding: bool,
    client: OpenAIClient,
    use_multi_agent: bool = True,
    max_correction_iterations: int = 3,
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

    # Hierarchical approach: mostly for parameter recognition
    if use_hierarchical:
        ode_str = hierarchical_approach(image_path, client)

    # One agent for the whole pipeline
    # Using a multi-agent approach to extract and validate the ODEs and concepts (2 agents)
    if use_multi_agent:
            #first agent
            concept_data = None
            if attempt_grounding:
                try:
                    concept_data = get_concepts_from_odes(ode_str, client)
                except Exception as e:
                    print(f"Warning: Concept extraction failed: {e}")
                    concept_data = None
            
            #second agent
            print("Running multi-agent validation...")
            corrected_ode_str, corrected_concepts = check_and_correct_extraction(
                ode_str, 
                concept_data, 
                client,
                max_iterations=max_correction_iterations
            )
            
            ode_str = corrected_ode_str
            concept_data = corrected_concepts
    else:
        if attempt_grounding:
            concept_data = get_concepts_from_odes(ode_str, client)
        else:
            concept_data = None

    # FixMe, for now use `exec` on the code, but need to find a safer way to execute
    # the code

    # Import sympy just in case the code snippet does not import it
    import sympy
    from sympy import Symbol, Function, Eq, Derivative
    odes: List[sympy.Eq] = None
    # Execute the code and expose the `odes` variable to the local scope
    local_dict =   {
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
        The validated TemplateModel
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