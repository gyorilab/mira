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
    verbose: bool = True,
    biomodel_name: str = None,
    correct_eqs_file_path: str = None
) -> tuple[str, Optional[dict], dict]:
    """
    Multi-agent pipeline for ODE extraction and validation
    
    Phase 1: Extract ODEs from image
    Phase 2: Extract concepts (grounding)
    Phase 3: Fix execution errors
    Phase 4: Validation checks
    Phase 5: Unified error correction
    Phase 6: Quantitative evaluation (comparison with ground truth)
    
    Args:
        image_path: Path to the image containing ODEs
        client: OpenAI client
        verbose: Whether to print progress
        biomodel_name: Name of the biomodel for ground truth comparison
        correct_eqs_file_path: Optional path to TSV file with correct equations
    
    Returns:
        Validated ODE string, concepts, and evaluation metrics
    """
    
    if verbose:
        print("="*60)
        print("MULTI-AGENT ODE EXTRACTION & VALIDATION PIPELINE")
        if biomodel_name:
            print(f"Biomodel: {biomodel_name}")
        print("="*60)
    
    # Phase 1: ODE Extraction from image
    ode_str = phase1_extract_odes(image_path, client, verbose)
    
    # Phase 2: Concept Grounding
    concepts = phase2_concept_grounding(ode_str, client, verbose)
    
    # Phase 3: Execution error correction
    ode_str = phase3_fix_execution_errors(ode_str, client, verbose)
    
    # Phase 4: Validation checks
    validation_reports = phase4_validation(ode_str, concepts, client, verbose)
    
    # Phase 5: Unified error correction
    ode_str, concepts, all_reports = phase5_unified_correction(
        ode_str, concepts, validation_reports, client, verbose
    )
    
    # Phase 6: Quantitative evaluation with comparison
    evaluation = phase6_quantitative_evaluation(
        ode_str, concepts, all_reports, client, verbose,
        biomodel_name=biomodel_name,
        correct_eqs_file_path=correct_eqs_file_path
    )
    
    if verbose:
        print("="*60)
        print("PIPELINE COMPLETE")
        print("="*60)
    
    return ode_str, concepts, evaluation


# PHASE 1: ODE EXTRACTION
def phase1_extract_odes(
    image_path: str, 
    client: OpenAIClient,
    verbose: bool = True
) -> str:
    """Phase 1: Extract ODEs from image using ODEExtractionSpecialist"""
    if verbose:
        print("\nPHASE 1: ODE Extraction from Image")
    
    from mira.sources.sympy_ode.agents import ODEExtractionSpecialist
    extractor = ODEExtractionSpecialist(client)
    result = extractor.process({'image_path': image_path})
    
    if verbose:
        print("  ODEs extracted from image")
        print(f"  Length: {len(result['ode_str'])} characters")
    
    return result['ode_str']


# PHASE 2: CONCEPT GROUNDING
def phase2_concept_grounding(
    ode_str: str,
    client: OpenAIClient,
    verbose: bool = True
) -> Optional[dict]:
    """Phase 2: Extract concepts from ODE string using ConceptGrounder"""
    if verbose:
        print("\nPHASE 2: Concept Grounding")
    
    from mira.sources.sympy_ode.agents import ConceptGrounder
    grounder = ConceptGrounder(client)
    result = grounder.process({'ode_str': ode_str})
    
    concepts = result.get('concepts')
    
    if verbose:
        if concepts:
            print(f"  Extracted {len(concepts)} concepts")
        else:
            print("  No concepts extracted")
    
    return concepts


# PHASE 3: EXECUTION ERROR CORRECTION
def phase3_fix_execution_errors(
    ode_str: str, 
    client: OpenAIClient,
    verbose: bool = True
) -> str:
    """Phase 3: Check and fix execution errors using ExecutionErrorCorrector"""
    if verbose:
        print("\nPHASE 3: Execution Error Correction")
    
    from mira.sources.sympy_ode.agents import ExecutionErrorCorrector
    corrector = ExecutionErrorCorrector(client)
    result = corrector.process({'ode_str': ode_str})
    
    if verbose:
        exec_report = result.get('execution_report', {})
        if exec_report.get('errors_fixed'):
            errors = exec_report['errors_fixed']
            print(f"  Fixed {len(errors)} error(s):")
            for i, error in enumerate(errors, 1):
                print(f"    Error {i}: {error}")
        elif exec_report.get('executable'):
            print("  No execution errors found")
        else:
            print("  Could not fix execution errors")
    
    return result['ode_str']


# PHASE 4: VALIDATION
def phase4_validation(
    ode_str: str, 
    concepts: Optional[dict],
    client: OpenAIClient,
    verbose: bool = True
) -> dict:
    """Phase 4: Run validation checks using ValidationAggregator and MathematicalAggregator"""
    if verbose:
        print("\nPHASE 4: Validation Checks")
    
    from mira.sources.sympy_ode.agents import ValidationAggregator, MathematicalAggregator
    
    # Run validation aggregator
    if verbose:
        print("  Running parameter and time-dependency validation...")
    val_aggregator = ValidationAggregator(client)
    val_results = val_aggregator.process({
        'ode_str': ode_str,
        'concepts': concepts
    })
    
    # Run mathematical aggregator
    if verbose:
        print("  Running mathematical validation...")
    math_aggregator = MathematicalAggregator(client)
    math_results = math_aggregator.process({'ode_str': ode_str})
    
    # Combine reports
    all_reports = {
        'validation_reports': val_results.get('validation_reports', {}),
        'mathematical_reports': math_results.get('mathematical_reports', {})
    }
    
    if verbose:
        # Count total issues found
        total_issues = 0
        for report in val_results.get('validation_reports', {}).values():
            total_issues += len(report.get('issues', []))
        for report in math_results.get('mathematical_reports', {}).values():
            total_issues += len(report.get('issues', []))
            total_issues += len(report.get('violations', []))
        
        if total_issues > 0:
            print(f"  Found {total_issues} issue(s) to correct")
        else:
            print("  No validation issues found")
    
    return all_reports


# PHASE 5: UNIFIED ERROR CORRECTION
def phase5_unified_correction(
    ode_str: str,
    concepts: Optional[dict],
    reports: dict,
    client: OpenAIClient,
    verbose: bool = True
) -> tuple[str, Optional[dict], dict]:
    """Phase 5: Apply unified corrections using UnifiedErrorCorrector"""
    if verbose:
        print("\nPHASE 5: Unified Error Correction")
    
    from mira.sources.sympy_ode.agents import UnifiedErrorCorrector
    
    corrector = UnifiedErrorCorrector(client)
    result = corrector.process({
        'ode_str': ode_str,
        'concepts': concepts,
        **reports
    })
    
    if verbose:
        corrections = result.get('corrections_report', {})
        if corrections.get('corrections_applied'):
            print(f"  Applied {len(corrections['corrections_applied'])} correction(s)")
        else:
            print("  No corrections needed")
    
    # Return corrected ODE, concepts, and updated reports
    return (
        result['ode_str'], 
        result.get('concepts', concepts),
        {**reports, 'corrections_report': result.get('corrections_report', {})}
    )


# PHASE 6: QUANTITATIVE EVALUATION
def phase6_quantitative_evaluation(
    ode_str: str, 
    concepts: Optional[dict], 
    reports: dict, 
    client: OpenAIClient, 
    verbose: bool = True,
    biomodel_name: str = None,
    correct_eqs_file_path: str = None
) -> dict:
    """
    Phase 6: Final quantitative evaluation using comparison with ground truth
    
    Args:
        ode_str: The corrected ODE string to evaluate
        concepts: Extracted concepts (optional)
        reports: Validation and correction reports from previous phases
        client: OpenAI client
        verbose: Whether to print progress
        biomodel_name: Name of the biomodel for loading correct equations
        correct_eqs_file_path: Path to TSV file with correct equations
    """
    if verbose:
        print("\nPHASE 6: Quantitative Evaluation (Comparison-Based)")
    
    if not biomodel_name:
        if verbose:
            print("  ERROR: No biomodel_name provided for comparison")
        return {
            'execution_success_rate': 0.0,
            'equation_accuracy_rate': 0.0,
            'error': 'No biomodel_name provided'
        }
    
    from mira.sources.sympy_ode.agents import QuantitativeEvaluator
    
    # Initialize evaluator with correct equations file path if provided
    if correct_eqs_file_path:
        evaluator = QuantitativeEvaluator(client, correct_eqs_file_path)
    else:
        evaluator = QuantitativeEvaluator(client)
    
    # Run the comparison-based evaluation
    result = evaluator.process({
        'ode_str': ode_str,
        'biomodel_name': biomodel_name,
        'concepts': concepts,
        **reports
    })
    
    # Print evaluation results
    if verbose:
        if 'error' in result:
            print(f"  ERROR: {result['error']}")
        else:
            exec_rate = result['execution_success_rate']
            eq_rate = result['equation_accuracy_rate']
            num_eqs = result.get('num_equations_checked', 0)
            
            # Count matching equations
            comparison_details = result.get('comparison_details', [])
            if isinstance(comparison_details, list):
                num_matching = sum(1 for d in comparison_details if d.get('match', False))
            else:
                num_matching = 0
            
            print(f"  Biomodel: {biomodel_name}")
            print(f"  Execution Success: {'PASS' if exec_rate == 1.0 else 'FAIL'} ({exec_rate:.0%})")
            print(f"  Equation Accuracy: {num_matching}/{num_eqs} equations match ({eq_rate:.1%})")
            
            
            # Show first few mismatches if any
            if comparison_details and isinstance(comparison_details, list):
                non_matching = [d for d in comparison_details if not d.get('match', False)]
                if non_matching:
                    print("\n  Non-matching equations (first 3):")
                    for detail in non_matching[:3]:
                        idx = detail.get('equation_index', '?')
                        diff = detail.get('difference', 'N/A')
                        if len(str(diff)) > 50:
                            diff_str = str(diff)[:50] + "..."
                        else:
                            diff_str = str(diff)
                        print(f"    Equation {idx}: Difference = {diff_str}")
    
    return {
        'execution_success_rate': result.get('execution_success_rate', 0.0),
        'equation_accuracy_rate': result.get('equation_accuracy_rate', 0.0),
        'comparison_details': result.get('comparison_details', []),
        'num_equations_checked': result.get('num_equations_checked', 0)
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