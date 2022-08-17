"""Neo4j client module."""

import flask

from .client import Neo4jClient
from .grounding import grounding_blueprint
from .utils import MiraState, PREFIXES

__all__ = [
    "app",
]

app = flask.Flask(__name__)

# Set MIRA_NEO4J_URL in the environment
# to point this somewhere specific
client = Neo4jClient()
app.config["mira"] = MiraState(
    client=client,
    grounder=client.get_grounder(PREFIXES),
)

app.register_blueprint(grounding_blueprint)

if __name__ == '__main__':
    app.run(host="0.0.0.0", port="8771")
