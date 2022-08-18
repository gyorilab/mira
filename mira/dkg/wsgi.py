"""Neo4j client module."""

import flask
from flasgger import Swagger
from flask_bootstrap import Bootstrap5

from .client import Neo4jClient
from .grounding import grounding_blueprint
from .ui import ui_blueprint
from .utils import PREFIXES, MiraState
from .api import api_blueprint

__all__ = [
    "app",
]

app = flask.Flask(__name__)

Swagger.DEFAULT_CONFIG.update(
    {
        "info": {
            "title": "MIRA Domain Knowledge Graph",
            "description": "A service for building and interacting with domain knowledge graphs",
        },
        # This is where the OpenAPI gets mounted
        "specs_route": "/apidocs/",
    }
)
Swagger(app)
Bootstrap5(app)

# Set MIRA_NEO4J_URL in the environment
# to point this somewhere specific
client = Neo4jClient()
app.config["mira"] = MiraState(
    client=client,
    grounder=client.get_grounder(PREFIXES),
)

app.register_blueprint(ui_blueprint)
app.register_blueprint(grounding_blueprint)
app.register_blueprint(api_blueprint, url_prefix="/api")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port="8771")
