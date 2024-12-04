import base64
import os
import unittest
from pathlib import Path

import requests

from mira.openai import OpenAIClient


@unittest.skipIf(os.environ.get('GITHUB_ACTIONS') is not None,
HERE = Path(__file__).parent.resolve()


                 reason="Meant to be run locally")
@unittest.skipIf(os.environ.get('OPENAI_API_KEY') is None,
                 reason="Need OPENAI_API_KEY environment variable to run")
def test_explain_image():
    bananas_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9b/Cavendish_Banana_DS.jpg/640px-Cavendish_Banana_DS.jpg"
    res = requests.get(bananas_url)
    base64_image = base64.b64encode(res.content).decode('utf-8')

    client = OpenAIClient()
    response = client.run_chat_completion_with_image(
        message="What is in this image?",
        base64_image=base64_image,
        image_format="jpeg",
    )
    assert "banana" in response.message.content, response.message.content


def test_extract_odes():
    equations_image = HERE / "ode_system.png"
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
    """
    client = OpenAIClient()

    # Load image and base64 encode it
    with open(equations_image, "rb") as f:
        base64_image = base64.b64encode(f.read()).decode("utf-8")

    response = client.run_chat_completion_with_image(
        message=prompt,
        image_format="png",
        base64_image=base64_image,
        max_tokens=1024 * 8,
    )

    print(response.message.content)
