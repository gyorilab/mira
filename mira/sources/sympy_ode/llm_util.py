import base64
import re
import logging
from typing import Optional, List, Union, Literal

from mira.metamodel import TemplateModel
from mira.openai import OpenAIClient, ImageFmts
from mira.sources.sympy_ode import template_model_from_sympy_odes
from mira.sources.sympy_ode.constants import (
    ODE_IMAGE_PROMPT,
    ODE_CONCEPTS_PROMPT_TEMPLATE,
    ODE_PDF_PROMPT,
    ODE_MULTIPLE_IMAGE_PROMPT
)

ContentType = Literal["pdf", "image", "text"]

logger = logging.getLogger(__name__)

ode_pattern_raw = r"(odes\s*=\s*\[.*?\])\s*"
ode_pattern = re.compile(ode_pattern_raw, re.DOTALL)


class CodeExecutionError(Exception):
    """An error raised when there is an error executing the code"""

def pdf_file_to_odes_str(
    pdf_path: str,
    client: OpenAIClient
) -> str:
    """Get an ODE string from a PDF file depicting an ODE system

    Parameters
    ----------
    pdf_path :
        The path to the PDF file
    client :
        A :class:`mira.openai.OpenAIClient` instance

    Returns
    -------
    :
        The ODE string extracted from the PDF. The string should contain the code
        necessary to define the ODEs using sympy.
    """
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    return pdf_to_odes_str(pdf_bytes, client)


def pdf_to_odes_str(
    pdf_bytes: bytes,
    client: OpenAIClient,
) -> str:
    """Get an ODE string from PDF bytes depicting an ODE system

    Parameters
    ----------
    pdf_bytes :
        The bytes of the PDF file
    client :
        The OpenAI client

    Returns
    -------
    :
        The ODE string extracted from the PDF. The string should contain the code
        necessary to define the ODEs using sympy.
    """

    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    response = extract_ode_str_from_base64_pdf(
        base64_pdf=base64_pdf,
        client=client
    )
    return response


def extract_ode_str_from_base64_pdf(
    base64_pdf: str,
    client: OpenAIClient,
    prompt: Optional[str] = None,
) -> str:
    """Get the ODE string from a PDF in base64 format

    Parameters
    ----------
    base64_pdf :
        The base64 encoded PDF
    client :
        The OpenAI client
    prompt :
        The prompt to send to the OpenAI chat completion. If None, the default
        prompt is used (see :data:`mira.sources.sympy_ode.constants.ODE_PDF_PROMPT`)

    Returns
    -------
    :
        The ODE string extracted from the PDF. The string should contain the code
        necessary to define the ODEs using sympy.
    """
    if prompt is None:
        prompt = ODE_PDF_PROMPT

    choice = client.run_chat_completion_with_pdf(
        message=prompt,
        base64_pdf=base64_pdf,
    )
    text_response = clean_response(choice.message.content)
    return text_response



def image_file_to_odes_str(
    image_path: Union[str, List[str]],
    client: OpenAIClient,
) -> str:
    """
    Get an ODE string from an image file or a list of image files depicting an
    ODE system

    Parameters
    ----------
    image_path :
        The path to the image file or a list of paths to each image file
    client :
        A :class:`mira.openai.OpenAIClient` instance

    Returns
    -------
    :
        The ODE string extracted from the image(s). The string should contain the
        code necessary to define the ODEs using sympy.
    """
    if isinstance(image_path, str):
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        image_format = image_path.split(".")[-1]
        return image_to_odes_str(image_bytes, client, image_format)
    else:
        image_bytes_list = []
        image_format_list = []
        for path in image_path:
            with open(path, "rb") as f:
                image_bytes = f.read()
                image_bytes_list.append(image_bytes)
            image_format = path.split(".")[-1]
            image_format_list.append(image_format)
        return image_to_odes_str(image_bytes_list, client, image_format_list)




def image_to_odes_str(
    image_bytes: Union[bytes, List[bytes]],
    client: OpenAIClient,
    image_format: Union[ImageFmts, List[ImageFmts]]
) -> str:
    """Get an ODE string from an image or a list of images depicting an ODE system

    Parameters
    ----------
    image_bytes :
        The bytes of the image or a list of bytes for each image
    client :
        The OpenAI client
    image_format :
        The format of the image or a list of formats for each image.

    Returns
    -------
    :
        The ODE string extracted from the image. The string should contain the code
        necessary to define the ODEs using sympy.
    """
    if not isinstance(image_bytes, List):
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        response = extract_ode_str_from_base64_image(base64_image=base64_image,
                                                     image_format=image_format,
                                                     client=client)
    else:
        base64_image_list = []
        for image_byte in image_bytes:
            base64_image = base64.b64encode(image_byte).decode('utf-8')
            base64_image_list.append(base64_image)
        response = extract_ode_str_from_base64_image(base64_image=base64_image_list,
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
    base64_image: Union[str, List[str]],
    image_format: Union[ImageFmts, List[ImageFmts]],
    client: OpenAIClient,
    prompt: str = None
):
    """Get the ODE string from an image or list of images in base64 format

    Parameters
    ----------
    base64_image :
        The base64 encoded image or a list of base64 encoded images
    image_format :
        The format of the image or a list of each image format
    client :
        The OpenAI client
    prompt :
        The prompt to send to the OpenAI chat completion. If None, the default
        prompt is used depending on if one or multiple images are sent
        (see :data:`mira.sources.sympy_ode.constants.ODE_IMAGE_PROMPT` and
        :data:`mira.sources.sympy_ode.constants.ODE_MULTIPLE_IMAGE_PROMPT`)

    Returns
    -------
    :
        The ODE string extracted from the image. The string should contain the code
        necessary to define the ODEs using sympy.
    """
    if prompt is None and not isinstance(base64_image, List):
        prompt = ODE_IMAGE_PROMPT
    elif prompt is None and isinstance(base64_image, List):
        prompt = ODE_MULTIPLE_IMAGE_PROMPT

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
    match = re.search(ode_pattern, ode_str)

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


def test_execution(code: str) -> bool:
    """Test if code executes successfully

    Parameters
    ----------
    code :
        The Python code

    Returns
    -------
    :
        Whether the code was exected successfully
    """
    try:
        namespace = {}
        exec("import sympy", namespace)
        exec(code, namespace)
        return 'odes' in namespace
    except Exception:
        return False
