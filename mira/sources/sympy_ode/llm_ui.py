from flask import Blueprint, render_template, request
from sympy import latex

from mira.modeling import Model
from mira.modeling.ode import OdeModel
from mira.modeling.amr.petrinet import AMRPetriNetModel

from .llm_util import execute_template_model_from_sympy_odes, image_to_odes_str
from .proxies import openai_client


llm_ui_blueprint = Blueprint("llm", __name__, url_prefix="/llm")

# Attach the template in this module to the blueprint
llm_ui_blueprint.template_folder = "templates"


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
            # get the image format
            image_format = file.content_type.split("/")[-1]
            result_text = image_to_odes_str(
                image_bytes=image_data,
                image_format=image_format,
                client=openai_client
            )

        # User submitted a result_text for processing
        elif result_text:
            template_model = execute_template_model_from_sympy_odes(
                result_text,
                attempt_grounding=True,
                client=openai_client
            )
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
