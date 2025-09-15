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


def run_multi_agent_pipeline(
    image_path: str,
    client: OpenAIClient,
    verbose: bool = True
) -> tuple[str, Optional[dict], dict]:
    """
    Multi-agent pipeline for ODE extraction and validation
    
    Phase 1: Extract ODEs and concepts from image
    Phase 2: Fix execution errors
    Phase 3: Validate and correct (parallel checks)
    Phase 4: Quantitative measures
    
    Returns:
        Validated ODE string, concepts, and quality score
    """
    
    if verbose:
        print("="*60)
        print("MULTI-AGENT ODE EXTRACTION & VALIDATION PIPELINE")
        print("="*60)
    
    # Phase 1: Extraction (part of pipeline for context tracking)
    ode_str, concepts = phase1_extract_odes(image_path, client, verbose)
    
    # Phase 2: Execution error correction
    ode_str = phase2_fix_execution_errors(ode_str, client, verbose)
    
    # Phase 3: Validation and mathematical correction
    ode_str, concepts = phase3_validate_and_correct(ode_str, concepts, client, verbose)
    
    # Phase 4: Quality evaluation
    evaluation = phase4_evaluate_quality(ode_str, concepts, {}, client, verbose)

    if verbose:
        print("="*60)
        print(f"\nExecution Success: {evaluation['execution_success_rate']:.0%}")
        print(f"Symbol Accuracy: {evaluation['symbol_accuracy_rate']:.1%}")
        print(f"Overall Score: {evaluation['overall_score']:.2%}")
    
    return ode_str, concepts, evaluation


# Individual phase functions
def phase1_extract_odes(
    image_path: str, 
    client: OpenAIClient,
    verbose: bool = True
) -> tuple[str, Optional[dict]]:
    """
    Phase 1: Extract ODEs and concepts from image
    Step 1: Extract ODE string from image
    Step 2: Extract concepts from ODE string
    """
    if verbose:
        print("\nPHASE 1: ODE Extraction & Concept Grounding")
    
    # Step 1: Image → ODE String
    if verbose:
        print("  Step 1: Extracting ODEs from image...")
    ode_str = image_file_to_odes_str(image_path, client)
    
    # Step 2: ODE String → Concepts (exactly as defined)
    if verbose:
        print("  Step 2: Extracting concepts from ODEs...")
    try:
        concepts = get_concepts_from_odes(ode_str, client)
        if verbose:
            print(f"  Extracted {len(concepts) if concepts else 0} concepts")
    except Exception as e:
        if verbose:
            print(f"    ⚠ Concept extraction failed: {e}")
        concepts = None
    
    return ode_str, concepts

def phase2_fix_execution_errors(
    ode_str: str, 
    client: OpenAIClient,
    verbose: bool = True
) -> str:
    """Phase 2: Check and fix execution errors"""
    if verbose:
        print("\nPHASE 2: Execution Error Check & Correction")
    
    from mira.sources.sympy_ode.agents import ExecutionErrorCorrector
    corrector = ExecutionErrorCorrector(client)
    result = corrector.process({'ode_str': ode_str})
    
    if verbose and result.get('execution_report', {}).get('errors_fixed'):
        print(f"  Fixed {len(result['execution_report']['errors_fixed'])} errors")
    
    return result['ode_str']

def phase3_validate_and_correct(
    ode_str: str, 
    concepts: Optional[dict],
    client: OpenAIClient,
    verbose: bool = True
) -> tuple[str, Optional[dict]]:
    """Phase 3: Validation and mathematical checks with corrections"""
    if verbose:
        print("\nPHASE 3: Validation & Mathematical Checks")
    
    from mira.sources.sympy_ode.agents import (
        ValidationAggregator,
        MathematicalAggregator,
        UnifiedErrorCorrector
    )
    
    pipeline_state = {'ode_str': ode_str, 'concepts': concepts}
    
    # Run parallel validation checks
    val_aggregator = ValidationAggregator(client)
    val_results = val_aggregator.process(pipeline_state)
    
    math_aggregator = MathematicalAggregator(client)
    math_results = math_aggregator.process(pipeline_state)
    
    # Apply unified corrections
    pipeline_state.update(val_results)
    pipeline_state.update(math_results)
    
    corrector = UnifiedErrorCorrector(client)
    correction_result = corrector.process(pipeline_state)
    
    return correction_result['ode_str'], correction_result.get('concepts', concepts)

def phase4_evaluate_quality(
    ode_str: str,
    concepts: Optional[dict],
    reports: dict,
    client: OpenAIClient,
    verbose: bool = True
) -> dict:
    """Phase 4: Quantitative evaluation of extraction quality"""
    if verbose:
        print("\nPHASE 4: Quantitative Evaluation")
    
    from mira.sources.sympy_ode.agents import QuantitativeEvaluator
    evaluator = QuantitativeEvaluator(client)
    
    result = evaluator.process({
        'ode_str': ode_str,
        'concepts': concepts,
        **reports
    })
    
    return {
        'execution_success_rate': result['execution_success_rate'],
        'symbol_accuracy_rate': result['symbol_accuracy_rate'],
        'overall_score': result['overall_score']
    }





def execute_template_model_from_sympy_odes(
    ode_str,
    concepts: Optional[dict] = None) -> TemplateModel:
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
    return template_model_from_sympy_odes(odes, concept_data=concepts)