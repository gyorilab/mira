from mira.openai import OpenAIClient

from flask import current_app
from werkzeug.local import LocalProxy


openai_client: OpenAIClient = LocalProxy(lambda: current_app.config["openai_client"])
