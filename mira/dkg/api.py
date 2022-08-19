"""API endpoints."""

from flask import Blueprint, jsonify, request
from neo4j.graph import Relationship

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
    """Get relations based on the query sent.

    The question *which hosts get immunized by the Brucella
    abortus vaccine strain 19?* translates to the following query:

        {"source_curie": "vo:0000022", "relation": "vo:0001243"}

    The question *which strains immunize mice?* translates
    to the following query:

        {"target_curie": "ncbitaxon:10090", "relation": vo:0001243"}
    ---
    parameters:
    - name: source_type
      description: The source type (i.e., prefix)
      in: body
      required: false
      example: doid
    - name: source_curie
      description: The source CURIE
      in: body
      required: false
      example: doid:946

    - name: target_type
      description: The target type (i.e., prefix)
      in: body
      required: false
      example: symp
    - name: target_curie
      description: The target CURIE
      in: body
      required: false
      example: symp:0000570

    - name: relations
      description: A relation string or list of relation strings
      in: body
      required: false
      example: vo:0001243
    - name: relation_direction
      description: The direction of the relationship
      in: body
      required: false
      example: right
      schema:
        type: string
        enum: ["right", "left", "both"]
        default: "right"
    - name: relation_min_hops
      description: The minimum number of hops between the entitis
      in: body
      required: false
      example: 1
      schema:
        type: integer
        minimum: 1
        default: 1
    - name: relation_max_hops
      description: The maximum number of hops between the entities. If 0 is given, makes infinite.
      in: body
      required: false
      example: 0
      schema:
        type: integer
        minimum: 0
        default: 1

    - name: limit
      description: A limit on the number of records returned
      in: body
      required: false
      example: 50
      schema:
        type: integer
        minimum: 1
    """
    if request.json.pop("full", False):
        records = client.query_relations(request.json, full=True)
        records = [
            (dict(s), dict(p) if isinstance(p, Relationship) else [dict(r) for r in p], dict(o)) for s, p, o in records
        ]
    else:
        records = client.query_relations(request.json, full=False)
    return jsonify(records)
