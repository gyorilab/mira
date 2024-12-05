from mira.openai import OpenAIClient

from flask import current_app
from werkzeug.local import LocalProxy


OPEN_AI_CLIENT = "openai_client"
openai_client: OpenAIClient = LocalProxy(lambda: current_app.extensions[OPEN_AI_CLIENT])
