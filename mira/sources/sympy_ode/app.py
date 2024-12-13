import os
from typing import List

from flask import Flask, request, render_template
import base64

from sympy import latex

from mira.metamodel import TemplateModel
from mira.modeling import Model
from mira.modeling.ode import OdeModel
from mira.openai import OpenAIClient
from mira.sources.sympy_ode import template_model_from_sympy_odes
from .proxies import openai_client, OPEN_AI_CLIENT

try:
    os.environ["OPENAI_API_KEY"]
except KeyError:
    raise ValueError("Set the OPENAI_API_KEY environment variable for run the app")


app = Flask(__name__)
app.extensions[OPEN_AI_CLIENT] = OpenAIClient()


def convert(base64_image, image_format, client: OpenAIClient, prompt: str = None):
    if prompt is None:
        prompt = """Transform these equations into a sympy representation based on the example style below

```python
# Define time variable
t = sympy.symbols("t")

# Define the time-dependent variables
S, E, I, R = sympy.symbols("S E I R", cls=sympy.Function)

# Define the parameters
b, g, r = sympy.symbols("b g r")

odes = [
    sympy.Eq(S(t).diff(t), - b * S(t) * I(t)),
    sympy.Eq(E(t).diff(t), b * S(t) * I(t) - r * E(t)),
    sympy.Eq(I(t).diff(t), r * E(t) - g * I(t)),
    sympy.Eq(R(t).diff(t), g * I(t))
]
```

Instead of using unicode characters, spell out in symbols in lowercase like theta, omega, etc.
Also, provide the code snippet only and no explanation."""

    choice = client.run_chat_completion_with_image(
        message=prompt,
        base64_image=base64_image,
        image_format=image_format,
    )
    text_response = choice.message.content
    if "```python" in text_response:
        text_response = text_response.replace("```python", "", 1)
    if "```" in text_response:
        text_response = text_response.replace("```", "", 1)
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


@app.route("/", methods=["GET", "POST"])
def upload_image():
    result_text = None
    ode_latex = None
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

    return render_template(
        "index.html",
        result_text=result_text,
        sympy_input=result_text,
        ode_latex=ode_latex,
    )


if __name__ == "__main__":
    app.run(debug=True, port=5000)
