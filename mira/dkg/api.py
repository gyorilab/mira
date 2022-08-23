"""API endpoints."""

from fastapi import APIRouter, Request
from flask import Blueprint, jsonify, request
from neo4j.graph import Relationship

from mira.dkg.client import Entity

from .proxies import client

__all__ = [
    "api_blueprint",
]

api_blueprint = APIRouter()


@api_blueprint.get("/entity/{curie}", response_model=Entity)
def get_entity(curie: str, request: Request):
    """Get information about an entity based on its compact URI (CURIE).

    Parameters
    ----------
    curie :
        A compact URI (CURIE) for an entity in the form of <prefix>:<local unique identifier>
    """
    # vo:0000001
    return request.app.neo4j_client.get_entity(curie)


@api_blueprint.get("/lexical")
def get_lexical():
    """Get information about an entity."""
    return request.app.neo4j_client.get_lexical()


@api_blueprint.post("/relations")
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
    query = dict(request.json)
    full = query.pop("full", False)
    records = client.query_relations(
        source_type=query.pop("source_type", None),
        source_curie=query.pop("source_curie", None),
        relation_name="r",
        relation_type=_get_relations(query),
        relation_direction=query.pop("relation_direction", "right"),
        relation_min_hops=query.pop("relation_min_hops", 1),
        relation_max_hops=query.pop("relation_max_hops", 1),
        target_name="t",
        target_type=query.pop("target_type", None),
        target_curie=query.pop("target_curie", None),
        full=full,
        distinct=query.pop("distinct", False),
        limit=query.pop("limit", None),
    )
    if query:
        print("invalid stuff remains in query:", query)
    if full:
        records = [
            (dict(s), dict(p) if isinstance(p, Relationship) else [dict(r) for r in p], dict(o)) for s, p, o in records
        ]
    return jsonify(records)


def _get_relations(query):
    for key in ("relation", "relations"):
        v = query.pop(key, None)
        if v is None:
            continue
        elif isinstance(v, str):
            break
        elif isinstance(v, list):
            return v
        else:
            raise TypeError(f"Invalid value type in {key}: {v}")
    return None
