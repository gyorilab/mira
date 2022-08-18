"""API endpoints."""

from flask import Blueprint, jsonify

from .proxies import client

__all__ = [
    "api_blueprint",
]

api_blueprint = Blueprint("api", __name__)


@api_blueprint.route("/parents/<curie>")
def get_parents(curie):
    """Get parents."""
    results = client.get_parents(curie)
    return jsonify(results)


@api_blueprint.route("/successors/<curie>/<relations>")
def get_successors(curie, relations):
    """Get successors.

    For example, the question *which hosts get immunized by the Brucella
    abortus vaccine strain 19?* translates to the following query:
    ``/successors/vo:0000022/vo:0001243``
    """
    results = client.get_successors(curie, relations.split(","))
    return jsonify(results)


@api_blueprint.route("/predecessors/<curie>/<relations>")
def get_predecessors(curie, relations):
    """Get predecessors.

    For example, the question *which strains immunize mice?* translates
    to: ``/predecessors/ncbitaxon:10090/vo:0001243``
    """
    results = client.get_predecessors(curie, relations.split(","))
    return jsonify(results)
