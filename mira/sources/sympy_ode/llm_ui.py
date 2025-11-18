import logging

from flask import Blueprint, render_template, request
from sympy import latex
import tempfile
import os

from mira.modeling import Model
from mira.modeling.ode import OdeModel
from mira.modeling.amr.petrinet import AMRPetriNetModel
from .llm_util import (
    execute_template_model_from_sympy_odes,
    image_to_odes_str,
    pdf_to_odes_str,
    CodeExecutionError,
)
from .agent_pipeline import run_multi_agent_pipeline
from .proxies import openai_client
from .paper_extraction import get_template_model_from_pmid


llm_ui_blueprint = Blueprint("llm", __name__, url_prefix="/llm")

# Attach the template in this module to the blueprint
llm_ui_blueprint.template_folder = "templates"


logger = logging.getLogger(__name__)


@llm_ui_blueprint.route("/", methods=["GET", "POST"])
def upload_image():
    result_text = None
    ode_latex = None
    petrinet_json_str = None
    input_type = "image"  # Default to image tab
    file, pmid = None, None

    if request.method == "POST":
        single_prompt = request.form.get("single_prompt") == "true"
        input_type = request.form.get("input_type")

        if input_type == "image":
            file = request.files.get("file")
        elif input_type == "pdf":
            file = request.files.get("pdf_file")
        elif input_type == "text":
            pmid = request.form.get("pmid_content")
        # Get the result_text from the form or the file uploaded
        result_text = request.form.get("result_text")

        # check if we have input or result_text
        if input_type in ["image", "pdf"]:
            #  If no file is selected or there is no result_text in the request
            if not file and not result_text:
                return render_template(
                    "index.html",
                    error=f"No {input_type} file provided",
                    active_input_type=input_type,
                    pmid_value=pmid,
                )
            # If a file is selected but the filename is empty and there is no result_text
            if file and file.filename == "" and not result_text:
                return render_template(
                    "index.html",
                    error="No selected file",
                    active_input_type=input_type,
                    pmid_value=pmid,
                )
        elif input_type == "text":
            if not pmid and not result_text:
                return render_template(
                    "index.html",
                    error="No PMID provided",
                    active_input_type=input_type,
                    pmid_value=pmid,
                )

        # User submitted a result_text for processing
        if result_text:
            try:
                template_model = execute_template_model_from_sympy_odes(
                    result_text, attempt_grounding=True, client=openai_client
                )
            except CodeExecutionError as e:
                # If there is an error executing the code, return the error message
                # and the result_text so that the user can see the error and correct
                # any mistakes in the input
                logger.exception(e)
                return render_template(
                    "index.html",
                    result_text=result_text,
                    error=str(e),
                    active_input_type=input_type,
                    pmid_value=pmid,
                )
            # Get the OdeModel
            om = OdeModel(
                model=Model(template_model=template_model), initialized=False
            )
            ode_system = om.get_interpretable_kinetics()
            ode_latex = latex(ode_system)
            # Get the PetriNet JSON
            petrinet_json_str = AMRPetriNetModel(
                Model(template_model)
            ).to_json_str(indent=2)

        # User uploaded a file/pmid with no result_text - process it
        elif input_type == "image" and file:
            if single_prompt:
                image_data = file.read()
                image_format = file.content_type.split("/")[-1]
                result_text = image_to_odes_str(
                    image_bytes=image_data,
                    image_format=image_format,
                    client=openai_client,
                )
            else:
                with tempfile.NamedTemporaryFile(
                    suffix=os.path.splitext(file.filename)[1], delete=False
                ) as temp_file:
                    file.save(temp_file.name)
                    temp_path = temp_file.name
                    # Need file path for multi-agent pipeline
                    result_text, _ = run_multi_agent_pipeline(
                        content_type="image",
                        image_path=temp_path,
                        client=openai_client,
                    )

        elif input_type == "pdf" and file:
            if single_prompt:
                pdf_data = file.read()
                result_text = pdf_to_odes_str(pdf_data, client=openai_client)
            else:
                with tempfile.NamedTemporaryFile(
                    suffix=".pdf", delete=False
                ) as temp_file:
                    file.save(temp_file.name)
                    temp_path = temp_file.name
                    result_text, _ = run_multi_agent_pipeline(
                        content_type="pdf",
                        image_path=temp_path,
                        client=openai_client,
                    )

        elif input_type == "text" and pmid:
            _, result_text = get_template_model_from_pmid(pmid=pmid)

    return render_template(
        "index.html",
        result_text=result_text,
        sympy_input=result_text,
        ode_latex=ode_latex,
        petrinet_json=petrinet_json_str,
        active_input_type=input_type,
        pmid_value=pmid,
    )
