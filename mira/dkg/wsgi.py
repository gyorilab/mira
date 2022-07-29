"""Neo4j client module."""

import random

import flask
from flask import request
from gilda.grounder import Grounder

from mira.dkg.client import Neo4jClient
from mira.dkg.construct import PREFIXES

app = flask.Flask(__name__)
client = Neo4jClient(url="bolt://localhost:7687")
grounder: Grounder = client.get_grounder(PREFIXES)


@app.route("/", methods=["GET"])
def home():
    key = random.choice(list(grounder.entries))
    return flask.jsonify(
        {
            "terms": len(grounder.entries),
            "example": {
                "key": key,
                "term": grounder.entries[key][0].to_json(),
            },
        }
    )


@app.route("/ground", methods=["POST"])
def ground():
    text = request.json.get("text")
    return _ground(text)


@app.route("/ground/<text>", methods=["GET"])
def ground_get(text: str):
    return _ground(text)


def _ground(text):
    results = grounder.ground(text)
    return flask.jsonify({"query": text, "results": [scored_match.to_json() for scored_match in results]})


if __name__ == "__main__":
    app.run(port="8762")
