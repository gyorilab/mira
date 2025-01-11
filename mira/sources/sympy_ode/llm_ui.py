import base64
from typing import List

from flask import Blueprint, render_template, request
from sympy import latex

from mira.openai import OpenAIClient
from mira.modeling import Model
from mira.metamodel import TemplateModel
from mira.modeling.ode import OdeModel
from mira.modeling.amr.petrinet import AMRPetriNetModel
from mira.sources.sympy_ode import template_model_from_sympy_odes

from .proxies import openai_client
from .constants import ODE_IMAGE_PROMPT, ODE_CONCEPTS_PROMPT_TEMPLATE


llm_ui_blueprint = Blueprint("llm", __name__, url_prefix="/llm")

# Attach the template in this module to the blueprint
llm_ui_blueprint.template_folder = "templates"


def clean_response(response: str) -> str:
    response = response.replace("```python", "")
    response = response.replace("```", "")
    return response.strip()


def convert(base64_image, image_format, client: OpenAIClient, prompt: str = None):
    if prompt is None:
        prompt = ODE_IMAGE_PROMPT

    choice = client.run_chat_completion_with_image(
        message=prompt,
        base64_image=base64_image,
        image_format=image_format,
    )
    text_response = clean_response(choice.message.content)
    return text_response


def execute_template_model_from_sympy_odes(ode_str) -> TemplateModel:
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
    return template_model_from_sympy_odes(odes)


@llm_ui_blueprint.route("/", methods=["GET", "POST"])
def upload_image():
    result_text = None
    ode_latex = None
    petrinet_json_str = None
    if request.method == "POST":
        # Get the result_text from the form or the file uploaded
        result_text = request.form.get("result_text")
        file = request.files.get("file")
        # If no file is selected or there is no result_text in the request
        if not file and not result_text:
            return render_template("index.html", error="No file part")

        # If a file is selected but the filename is empty and there is no result_text
        if file is not None and file.filename == '' and not result_text:
            return render_template("index.html", error="No selected file")

        # User uploaded a file but there is no result_text
        if file and not result_text:
            # Convert file to base64
            image_data = file.read()
            base64_image = base64.b64encode(image_data).decode('utf-8')
            # get the image format
            image_format = file.content_type.split("/")[-1]
            # Call the 'convert' function
            result_text = convert(
                base64_image=base64_image,
                client=openai_client,
                image_format=image_format
            )

        # User submitted a result_text for processing
        elif result_text:
            template_model = execute_template_model_from_sympy_odes(result_text)
            # Get the OdeModel
            om = OdeModel(model=Model(template_model=template_model), initialized=False)
            ode_system = om.get_interpretable_kinetics()
            # Make LaTeX representation of the ODE system
            ode_latex = latex(ode_system)

            # Get the PetriNet JSON
            petrinet_json_str = AMRPetriNetModel(Model(template_model)).to_json_str(indent=2)

    return render_template(
        "index.html",
        result_text=result_text,
        sympy_input=result_text,
        ode_latex=ode_latex,
        petrinet_json=petrinet_json_str,
    )
