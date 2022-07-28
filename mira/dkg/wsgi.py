"""Neo4j client module."""

import flask
from flask import request

from mira.dkg.client import Neo4jClient

app = flask.Flask(__name__)
client = Neo4jClient(url="bolt://localhost:7687")
grounder = client.get_grounder("go")


@app.route("/ground", methods=["POST"])
def ground():
    text = request.json.get("text")
    results = grounder.ground(text)
    return flask.jsonify([scored_match.to_json() for scored_match in results])


if __name__ == "__main__":
    app.run(port="8762")
