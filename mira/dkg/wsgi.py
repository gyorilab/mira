"""Neo4j client module."""

import flask
from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from flasgger import Swagger
from flask_bootstrap import Bootstrap5

from mira.dkg.api import api_blueprint
from mira.dkg.client import Neo4jClient
from mira.dkg.grounding import grounding_blueprint
from mira.dkg.ui import ui_blueprint
from mira.dkg.utils import PREFIXES, MiraState

__all__ = [
    "flask_app",
]

app = FastAPI(
    title="MIRA Domain Knowledge Graph",
    description="A service for building and interacting with domain knowledge graphs",
)
app.include_router(api_blueprint, prefix="/api")

flask_app = flask.Flask(__name__)

Bootstrap5(flask_app)

# Set MIRA_NEO4J_URL in the environment
# to point this somewhere specific
client = Neo4jClient()
flask_app.config["mira"] = MiraState(
    client=client,
    grounder=client.get_grounder(PREFIXES),
)

flask_app.register_blueprint(ui_blueprint)
flask_app.register_blueprint(grounding_blueprint)

app.mount("/", WSGIMiddleware(flask_app))
app.client = client
