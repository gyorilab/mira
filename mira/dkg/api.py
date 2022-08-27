"""API endpoints."""

from typing import List, Optional, Union

from fastapi import APIRouter, Request
from neo4j.graph import Relationship
from pydantic import BaseModel, Field
from typing_extensions import Literal

from mira.dkg.client import Entity, LexicalRow

__all__ = [
    "api_blueprint",
]

api_blueprint = APIRouter()


class RelationQuery(BaseModel):
    """A query for relations in the domain knowledge graph."""

    source_type: Optional[str] = Field(description="The source type (i.e., prefix)", example="vo")
    source_curie: Optional[str] = Field(
        description="The source compact URI (CURIE)", example="doid:946"
    )
    target_type: Optional[str] = Field(
        description="The target type (i.e., prefix)", example="ncbitaxon"
    )
    target_curie: Optional[str] = Field(
        description="The target compact URI (CURIE)", example="ncbitaxon:10090"
    )
    relations: Union[None, str, List[str]] = Field(
        description="A relation string or list of relation strings", example="vo:0001243"
    )
    relation_direction: Literal["right", "left", "both"] = Field(
        "right", description="The direction of the relationship"
    )
    relation_min_hops: int = Field(
        1, description="The minimum number of relationships between the subject and object.", ge=1
    )
    relation_max_hops: int = Field(
        1,
        description="The maximum number of relationships between the subject and object. Set to 0 to make infinite.",
        ge=0,
    )
    limit: Optional[int] = Field(
        description="A limit on the number of records returned", example=50, ge=0
    )
    full: bool = Field(
        False,
        description="A flag to turn on full entity and relation metadata return. Warning, this gets pretty verbose.",
    )
    distinct: bool = Field(
        False, description="A flag to turn on the DISTINCT flag in the return of a cypher query"
    )


@api_blueprint.get("/entity/{curie}", response_model=Entity, tags=["entities"])
def get_entity(curie: str, request: Request):
    """Get information about an entity based on its compact URI (CURIE).

    Parameters
    ----------
    curie :
        A compact URI (CURIE) for an entity in the form of <prefix>:<local unique identifier>
    """
    # vo:0000001
    return request.app.state.client.get_entity(curie)


@api_blueprint.get("/lexical", response_model=List[LexicalRow], tags=["entities"])
def get_lexical(request: Request):
    """Get information about an entity."""
    return request.app.state.client.get_lexical()


@api_blueprint.post("/relations", response_model=List, tags=["relations"])
def get_relations(relation_query: RelationQuery, request: Request):
    """Get relations based on the query sent.

    The question *which hosts get immunized by the Brucella
    abortus vaccine strain 19?* translates to the following query:

        {"source_curie": "vo:0000022", "relation": "vo:0001243"}

    The question *which strains immunize mice?* translates
    to the following query:

        {"target_curie": "ncbitaxon:10090", "relation": vo:0001243"}

    Note that you will rarely use all possible values in this endpoint at the same time.
    """
    records = request.app.state.client.query_relations(
        source_type=relation_query.source_type,
        source_curie=relation_query.source_curie,
        relation_name="r",
        relation_type=query.relations,
        relation_direction=relation_query.relation_direction,
        relation_min_hops=relation_query.relation_min_hops,
        relation_max_hops=relation_query.relation_max_hops,
        target_name="t",
        target_type=relation_query.target_type,
        target_curie=relation_query.target_curie,
        full=relation_query.full,
        distinct=relation_query.distinct,
        limit=relation_query.limit,
    )
    if relation_query.full:
        records = [
            (dict(s), dict(p) if isinstance(p, Relationship) else [dict(r) for r in p], dict(o))
            for s, p, o in records
        ]
    return records
