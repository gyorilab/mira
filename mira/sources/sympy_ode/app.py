"""
To run the LLM UI as a standalone app:
1. Set the OPENAI_API_KEY environment variable to your OpenAI API key.
2. Have the openai Python package installed (pip install openai).
3. Run with `python -m mira.sources.sympy_ode.app`. Optionally, pass in `debug`
   as an argument to run in debug mode (will reload the server on changes).
"""
import os
from flask import Flask
from mira.openai import OpenAIClient
from .llm_ui import llm_ui_blueprint
from .proxies import OPEN_AI_CLIENT

try:
    os.environ["OPENAI_API_KEY"]
except KeyError:
    raise ValueError("Set the OPENAI_API_KEY environment variable to run the app")


app = Flask(__name__)
app.extensions[OPEN_AI_CLIENT] = OpenAIClient()

app.register_blueprint(llm_ui_blueprint)


if __name__ == "__main__":
    import sys
    debug = len(sys.argv) > 1 and sys.argv[1].lower() == "debug"
    app.run(debug=debug, port=5000)
