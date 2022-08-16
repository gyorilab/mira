"""Gilda grounding blueprint."""

import random

import flask
from flask import Blueprint, request, Response
from gilda.grounder import ScoredMatch

from .proxies import grounder

__all__ = [
    "grounding_blueprint",
]

grounding_blueprint = Blueprint("grounding", __name__)


@grounding_blueprint.route("/", methods=["GET"])
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


@grounding_blueprint.route("/ground", methods=["POST"])
def ground():
    text = request.json.get("text")
    return _ground(text)


@grounding_blueprint.route("/ground/<text>", methods=["GET"])
def ground_get(text: str):
    return _ground(text)


def _ground(text: str) -> Response:
    results = grounder.ground(text)
    return flask.jsonify({"query": text, "results": [_unwrap(scored_match) for scored_match in results]})


def _unwrap(scored_match: ScoredMatch):
    scored_match_json = scored_match.to_json()
    return {
        "url": scored_match_json["score"],
        "score": scored_match_json["score"],
        **scored_match_json["term"],
    }
