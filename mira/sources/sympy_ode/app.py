import os

from flask import Flask, request, render_template
import base64

from mira.openai import OpenAIClient
from .proxies import openai_client

try:
    os.environ["OPENAI_API_KEY"]
except KeyError:
    raise ValueError("Set the OPENAI_API_KEY environment variable for run the app")


app = Flask(__name__)


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


@app.route("/", methods=["GET", "POST"])
def upload_image():
    result_text = None
    if request.method == "POST":
        if 'file' not in request.files:
            return render_template("index.html", error="No file part")

        file = request.files['file']
        if file.filename == '':
            return render_template("index.html", error="No selected file")

        if file:
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

    return render_template("index.html", result_text=result_text)


if __name__ == "__main__":
    app.config["openai_client"] = OpenAIClient()
    app.run(debug=True, port=5000)
