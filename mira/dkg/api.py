"""API endpoints."""

from flask import Blueprint, jsonify, request

from .proxies import client

__all__ = [
    "api_blueprint",
]

api_blueprint = Blueprint("api", __name__)


@api_blueprint.route("/entity/<curie>")
def get_entity(curie):
    """Get information about an entity

    ---
    parameters:
    - name: curie
      description: A compact URI (CURIE)
      in: path
      required: true
      example: vo:0000001
    """
    return jsonify(client.get_entity(curie))


@api_blueprint.route("/lexical")
def get_lexical():
    """Get information about an entity.

    ---
    """
    return jsonify(client.get_lexical())


@api_blueprint.route("/relations", methods=["POST"])
def get_relations():
    """Get relations based on the query sent."""
    if request.json.get("full"):
        records = client.query_relations(request.json, full=True)
        records = [(dict(s), dict(p), dict(o)) for s, p, o in records]
    else:
        records = client.query_relations(request.json, full=False)
    return jsonify(records)


@api_blueprint.route("/successors/<curie>/<relations>")
def get_successors(curie, relations):
    """Get successors.

    For example, the question *which hosts get immunized by the Brucella
    abortus vaccine strain 19?* translates to the following query:
    ``/successors/vo:0000022/vo:0001243``

    ---
    parameters:
    - name: curie
      description: A compact URI (CURIE)
      in: path
      required: true
      example: vo:0000022
    - name: relations
      description: A comma-separated list of relations (either as CURIEs or internal labels)
      in: path
      required: true
      example: vo:0001243
    """
    return jsonify(client.get_successors(curie, relations.split(",")))


@api_blueprint.route("/predecessors/<curie>/<relations>")
def get_predecessors(curie, relations):
    """Get predecessors.

    For example, the question *which strains immunize mice?* translates
    to: ``/predecessors/ncbitaxon:10090/vo:0001243``

    ---
    parameters:
    - name: curie
      description: A compact URI (CURIE)
      in: path
      required: true
      example: ncbitaxon:10090
    - name: relations
      description: A comma-separated list of relations (either as CURIEs or internal labels)
      in: path
      required: true
      example: vo:0001243
    """
    return jsonify(client.get_predecessors(curie, relations.split(",")))
