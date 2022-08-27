"""Neo4j client module."""

from textwrap import dedent

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
    "app",
]

tags_metadata = [
    {
        "name": "grounding",
        "description": "Identify appropriate ontology/database terms for text using Gilda.",
        "externalDocs": {
            # "description": "Gilda is a Python package and REST service that grounds (i.e., finds appropriate identifiers in namespaces for) named entities in biomedical text.",
            "url": "https://github.com/indralab/gilda",
        },
    },
]


app = FastAPI(
    openapi_tags=tags_metadata,
    title="MIRA Domain Knowledge Graph",
    description=dedent(
        """\
    A service for building and interacting with domain knowledge graphs.

    Further information can be found at:
    - https://github.com/indralab/mira
    """
    ),
    contact={
        "name": "Benjamin M. Gyori",
        "email": "benjamin_gyori@hms.harvard.edu",
    },
    license_info={
        "name": "BSD-2-Clause license",
        "url": "https://github.com/indralab/mira/blob/main/LICENSE",
    },
)
app.include_router(api_blueprint, prefix="/api")
app.include_router(grounding_blueprint, prefix="/api")

flask_app = flask.Flask(__name__)

Bootstrap5(flask_app)

# Set MIRA_NEO4J_URL in the environment
# to point this somewhere specific
client = Neo4jClient()
app.state = flask_app.config["mira"] = MiraState(
    client=client,
    grounder=client.get_grounder(PREFIXES),
)

flask_app.register_blueprint(ui_blueprint)

app.mount("/", WSGIMiddleware(flask_app))
