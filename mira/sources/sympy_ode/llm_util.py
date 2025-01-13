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


def image_file_to_odes_str(
    image_path: str,
    client: OpenAIClient,
) -> str:
    with open(image_path, "rb") as f:
        image_bytes = f.read()
    image_format = image_path.split(".")[-1]
    return image_to_odes_str(image_bytes, client, image_format)


def image_to_odes_str(
    image_bytes: bytes,
    client: OpenAIClient,
    image_format: ImageFmts = "png"
) -> str:
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    response = extract_ode_str_from_base64_image(base64_image=base64_image,
                                                 image_format=image_format,
                                                 client=client)
    return response


def clean_response(response: str) -> str:
    response = response.replace("```python", "")
    response = response.replace("```", "")
    return response.strip()


def extract_ode_str_from_base64_image(
    base64_image: str,
    image_format: ImageFmts,
    client: OpenAIClient,
    prompt: str = None
):
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
    """

    Parameters
    ----------
    ode_str :
        The string containing the code snippet defining the ODEs
    client :
        The openAI client

    Returns
    -------
    :
        The concepts data in the form of a dictionary
    """
    # Cut out the part of the code that defines the `odes` variable
    # Regular expression to capture the `odes` variable assignment and definition
    match = re.search(pattern, ode_str)

    if match:
        odes_code = match.group(1)
    else:
        raise ValueError("No code snippet defining the variable `odes` found")

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


def execute_template_model_from_sympy_odes(
    ode_str,
    attempt_grounding: bool,
    client: OpenAIClient,
) -> TemplateModel:
    # FixMe, for now use `exec` on the code, but need to find a safer way to execute
    #  the code
    # Import sympy just in case the code snippet does not import it
    import sympy
    odes: List[sympy.Eq] = None
    # Execute the code and expose the `odes` variable to the local scope
    local_dict = locals()
    exec(ode_str, globals(), local_dict)
    # `odes` should now be defined in the local scope
    odes = local_dict.get("odes")
    assert odes is not None, "The code should define a variable called `odes`"
    if attempt_grounding:
        concept_data = get_concepts_from_odes(ode_str, client)
    else:
        concept_data = None
    return template_model_from_sympy_odes(odes, concept_data=concept_data)
