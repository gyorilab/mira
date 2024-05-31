"""API endpoints."""

import itertools as itt
from typing import Any, List, Mapping, Optional, Union
import uuid

import pydantic
from fastapi import APIRouter, Body, HTTPException, Path, Query, Request, BackgroundTasks
from fastapi.responses import FileResponse
from neo4j.graph import Relationship
from pydantic import BaseModel, Field
from scipy.spatial import distance
from typing_extensions import Literal
import networkx as nx
import pystow

from mira.dkg.client import AskemEntity, Entity
from mira.dkg.utils import DKG_REFINER_RELS

__all__ = [
    "api_blueprint",
]

api_blueprint = APIRouter()

viz_temp = pystow.module("mira", "tmp")


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


@api_blueprint.get(
    "/entity/{curie}",
    # Note the order is important here - is greedy from left to right
    response_model=Union[AskemEntity, Entity],
    response_model_exclude_unset=True,
    response_model_exclude_defaults=True,
    response_model_exclude_none=True,
    tags=["entities"],
)
def get_entity(
    request: Request,
    curie: str = Path(
        ...,
        description="A compact URI (CURIE) for an entity in the form of ``<prefix>:<local unique identifier>``",
        examples=["ido:0000511"],
    ),
):
    """Get information about an entity (e.g., its name, description synonyms, alternative identifiers,
    database cross-references, etc.) debased on its compact URI (CURIE).
    """
    return _get_entity(request, curie)


@api_blueprint.get(
    "/entities/{curies}",
    # Note the order is important here - is greedy from left to right
    response_model=List[Union[AskemEntity, Entity]],
    response_model_exclude_unset=True,
    response_model_exclude_defaults=True,
    response_model_exclude_none=True,
    tags=["entities"],
)
def get_entities(
    request: Request,
    curies: str = Path(
        ...,
        description="A comma-separated list of compact URIs (CURIEs) for an "
        "entity in the form of ``<prefix>:<local unique identifier>,...``",
        examples=["ido:0000511,ido:0000512"],
    ),
):
    """
    Get information about multiple entities (e.g., their names, description synonyms,
    alternative identifiers, database cross-references, etc.) based on their
    respective compact URIs (CURIEs).
    """
    return [
        _get_entity(request, curie.strip())
        for curie in curies.split(",")
    ]


def _get_entity(request: Request, curie: str) -> Union[AskemEntity, Entity]:
    try:
        rv = request.app.state.client.get_entity(curie)
    except pydantic.ValidationError:
        raise HTTPException(
            status_code=500,
            detail=f"Malformed data in DKG for {curie}"
        ) from None
    if rv is None:
        raise HTTPException(
            status_code=404,
            detail=f"Could not find resource in the DKG for {curie}"
        )
    return rv


@api_blueprint.get(
    "/lexical",
    response_model=List[Entity],
    tags=["entities"],
    response_model_include={"name", "synonyms", "description", "id"},
    response_model_exclude_unset=True,
    response_description="A successful response contains a list of Entity objects, subset to only "
    "include the id, name, synonyms, and description fields. Note that below "
    "in the example, several additional fields are shown, but they are not actually returned.",
)
def get_lexical(request: Request):
    """Get lexical information (i.e., name, synonyms, and description) for all entities in the graph."""
    return request.app.state.lexical_dump


@api_blueprint.get(
    "/transitive_closure",
    response_model=List[List[str]],
    tags=["relations"],
    response_description="A successful response contains a list of entity "
    "pairs, representing a transitive closure set for the relations of the "
    "requested type(s). The pairs are ordered as (successor, descendant). "
    "Note that if the relations are ones that point towards taxonomical "
    "parents (e.g., subclassof, part_of), then the pairs are interpreted as "
    "(taxonomical child, taxonomical ancestor).",
)
def get_transitive_closure(
    request: Request,
    relation_types: List[str] = Query(
        ...,
        description="A list of relation types to get a transitive closure for",
        examples=[DKG_REFINER_RELS],
    ),
):
    """Get a transitive closure of the requested type(s)"""
    # The closure of the refiner relations are cached in the app state and can
    # be returned immediately
    if set(relation_types) == set(DKG_REFINER_RELS):
        return list(request.app.state.refinement_closure.transitive_closure)
    # Other relations have to be queried for
    else:
        return list(
            request.app.state.client.get_transitive_closure(rels=relation_types)
        ) or []


class RelationResponse(BaseModel):
    """A triple (or multi-predicate triple) with abbreviated data."""

    subject: str = Field(description="The CURIE of the subject of the triple", example="doid:96")
    predicate: Union[str, List[str]] = Field(
        description="A predicate or list of predicates as CURIEs",
        example="ro:0002452",
    )
    object: str = Field(description="The CURIE of the object of the triple", example="symp:0000001")


class FullRelationResponse(BaseModel):
    """A triple (or multi-preficate triple) with full data."""

    subject: Entity
    predicate: Union[Mapping[str, Any], List[Mapping[str, Any]]]
    object: Entity


@api_blueprint.post(
    "/relations",
    response_model=Union[List[RelationResponse], List[FullRelationResponse]],
    tags=["relations"],
)
def get_relations(
    request: Request,
    relation_query: RelationQuery = Body(
        ...,
        examples={
            "source type query": {
                "summary": "Query relations with a given source node type",
                "value": {
                    "source_type": "vo",
                    "limit": 2,
                },
            },
            "target type query": {
                "summary": "Query relations with a given target node type",
                "value": {
                    "target_type": "stmp",
                    "limit": 2,
                },
            },
            "source/target types query": {
                "summary": "Query relations with given source/target types",
                "value": {
                    "source_type": "doid",
                    "target_type": "symp",
                    "limit": 2,
                },
            },
            "source query": {
                "summary": "Query relations with given source node, by CURIE",
                "value": {
                    "source_node": "doid:946",
                },
            },
            "target query": {
                "summary": "Query relations with given target node, by CURIE",
                "value": {
                    "target_node": "symp:0000570",
                },
            },
            "single relation type query": {
                "summary": "Query relations with given single relation type",
                "value": {"relation": "rdfs:subClassOf", "limit": 2},
            },
            "multiple relation type query": {
                "summary": "Query relations with given relation types",
                "value": {"relation": ["rdfs:subClassOf", "bfo:0000050"], "limit": 2},
            },
            "increase path length of query": {
                "summary": "Query a given fixed number of hops",
                "value": {
                    "source_curie": "bfo:0000002",
                    "relation": "rdfs:subClassOf",
                    "relation_max_hops": 2,
                    "limit": 2,
                },
            },
            "any path length allowed": {
                "summary": "Query a variable number of hops",
                "description": "Distinct is given as true since there might be multiple paths from the source to each given target.",
                "value": {
                    "source_curie": "bfo:0000002",
                    "relation": "rdfs:subClassOf",
                    "relation_max_hops": 0,
                    "limit": 2,
                    "distinct": True,
                },
            },
            "full results with single relation": {
                "summary": "Example query with a single predicate returning full data",
                "value": {
                    "target_curie": "symp:0000570",
                    "limit": 2,
                    "full": True,
                },
            },
            "full results with multiple relations relation": {
                "summary": "Example query with multiple predicates returning full data",
                "value": {
                    "source_curie": "bfo:0000002",
                    "relation": "rdfs:subClassOf",
                    "relation_max_hops": 0,
                    "limit": 2,
                    "distinct": True,
                    "full": True,
                },
            },
        },
    ),
):
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
        relation_type=relation_query.relations,
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
        return [
            FullRelationResponse(
                subject=Entity.from_data(s),
                predicate=dict(p) if isinstance(p, Relationship) else [dict(r) for r in p],
                object=Entity.from_data(o),
            )
            for s, p, o in records
        ]
    else:
        return [RelationResponse(subject=s, predicate=p, object=o) for s, p, o in records]


@api_blueprint.post(
    "/relations_graph",
    response_model=None,
    tags=["relations"],
)
def get_relations_graph(
    request: Request,
    background_tasks: BackgroundTasks,
    relation_query: RelationQuery = Body(
        ...,
    )
):
    """Get an image of the relations based on the query sent. This endpoint takes in the same
    exact parameters as the /relations endpoint.

    The question *which hosts get immunized by the Brucella
    abortus vaccine strain 19?* translates to the following query:

        {"source_curie": "vo:0000022", "relation": "vo:0001243"}

    The question *which strains immunize mice?* translates
    to the following query:

        {"target_curie": "ncbitaxon:10090", "relation": vo:0001243"}

    Note that you will rarely use all possible values in this endpoint at the same time.
    Instead of returning a list of all relations retrieved from the query, a png image will
    be returned of the subgraph created from the query sent.
    """
    records = request.app.state.client.query_relations(
        source_type=relation_query.source_type,
        source_curie=relation_query.source_curie,
        relation_name="r",
        relation_type=relation_query.relations,
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

    fo = viz_temp.join(name=f"{uuid.uuid4()}.png")
    posix_str = fo.absolute().as_posix()

    graph = nx.DiGraph()
    graph.graph["rankdir"] = "LR"

    for relation in records:
        if relation_query.full:
            subject = Entity.from_data(relation[0])
            subject_curie = subject.id
            subject_name = subject.name
            p = relation[1]
            predicate_dict = dict(p) if isinstance(p, Relationship) else [dict(r) for r in p]
            predicate_name = p.type
            predicate_curie = predicate_dict["pred"]
            object = Entity.from_data(relation[2])
            object_curie = object.id
            object_name = object.name

            subject_node = f"{subject_name} ({subject_curie})"
            predicate_edge = f"{predicate_name} ({predicate_curie})"
            object_node = f"{object_name} ({object_curie})"

            graph.add_edge(subject_node, object_node, label=predicate_edge,
                           color="red", weight=2)
        else:
            graph.add_edge(relation[0], relation[2], label=relation[1],
                           color="red", weight=2)
    agraph = nx.nx_agraph.to_agraph(graph)
    try:
        agraph.draw(path=posix_str, prog="dot", format="png")
    except Exception as exc:
        raise exc
    finally:
        background_tasks.add_task(_delete_after_response, fo)
    return FileResponse(
        path=posix_str, media_type="image/png", filename=f"model.png"
    )


def _delete_after_response(tmp_file: Union[str, Path]):
    tmp_file.unlink(missing_ok=True)


class IsOntChildResult(BaseModel):
    """Result of a query to /is_ontological_child"""

    child_curie: str = Field(...,
                             example="vo:0001113",
                             description="The child CURIE")
    parent_curie: str = Field(...,
                              example="obi:0000047",
                              description="The parent CURIE")
    is_child: bool = Field(
        ...,
        description="True if the child CURIE is an ontological child of the "
                    "parent CURIE"
    )


class IsOntChildQuery(BaseModel):
    """Query for /is_ontological_child"""

    child_curie: str = Field(..., description="The child CURIE")
    parent_curie: str = Field(..., description="The parent CURIE")


@api_blueprint.post(
    "/is_ontological_child",
    response_model=IsOntChildResult,
    tags=["relations"]
)
def is_ontological_child(
    request: Request,
    query: IsOntChildQuery = Body(
        ...,
        example={"child_curie": "vo:0001113", "parent_curie": "obi:0000047"},
    )
):
    """Check if one CURIE is an ontological child of another CURIE"""
    return IsOntChildResult(
        child_curie=query.child_curie,
        parent_curie=query.parent_curie,
        is_child=request.app.state.refinement_closure.is_ontological_child(
            child_curie=query.child_curie,
            parent_curie=query.parent_curie
        )
    )


@api_blueprint.get(
    "/search",
    response_model=List[Union[AskemEntity, Entity]],
    response_model_exclude_unset=True,
    response_model_exclude_none=True,
    response_model_exclude_defaults=True,
    tags=["grounding"],
)
def search(
    request: Request,
    q: str = Query(..., examples=["infect"], description="The search query"),
    limit: int = 25,
    offset: int = 0,
    prefixes: Optional[str] = Query(
        default=None,
        description="A comma-separated list of prefixes",
        examples=[{
            "no prefix filter": {
                "summary": "Don't filter by prefix",
                "value": None,
            },
            "search for units": {
                "summary": "Search for units, which have Wikidata prefixes",
                "value": "wikidata",
            },
        }],
    ),
    labels: Optional[str] = Query(
        default=None,
        description="A comma-separated list of labels",
        examples={
            "no label filter": {
                "summary": "Don't filter by label",
                "value": None,
            },
            "search for units": {
                "summary": "Search for units, which are labeled as `unit`",
                "value": "unit",
            },
        },
    ),
    wikidata_fallback: bool = Query(
        default=False,
        description="Use Wikidata search if no entities returned from DKG search",
    ),
):
    """Get nodes based on a search to their name/synonyms."""
    return request.app.state.client.search(
        q,
        limit=limit,
        offset=offset,
        prefixes=prefixes and prefixes.split(","),
        labels=labels and labels.split(","),
        wikidata_fallback=wikidata_fallback,
    )


class ParentQuery(BaseModel):
    curie1: str = Field(..., description="The first CURIE")
    curie2: str = Field(..., description="The second CURIE")


@api_blueprint.post(
    "/common_parent",
    response_model=List[Entity],
    tags=["relations"],
)
def common_parent(
    request: Request,
    query: ParentQuery = Body(
        ..., example={"curie1": "ido:0000566", "curie2": "ido:0000567"}
    ),
):
    """Get the common parent of two CURIEs"""
    entity = request.app.state.client.get_common_parents(query.curie1,
                                                         query.curie2)
    return entity


class NormalizedCosineSimilarity(BaseModel):
    """Represents the normalized cosine similarity between two entities.

    The cosine similarity between two vectors is defined as the dot product
    between the vectors divided by the L2 norm (i.e., magnitude) of each
    vector. It ranges from [-1,1], where -1 represents two entities that are
    very dissimilar, 0 represents entities that are not similar, and 1 represents
    entities that are similar. This is calculated using :func:`scipy.spatial.distance.cosine`.

    We normalize this onto a range of [0,1] such that 0 means very dissimilar, 0.5
    means not similar, and 1 means similar. This is accomplished with the transform:

    .. code:: python

        normalized_cosine = (2 - scipy.spatial.distance.cosine(X, Y)) / 2
    """

    source: str = Field(..., title="source CURIE")
    target: str = Field(..., title="target CURIE")
    similarity: float = Field(
        ..., title="normalized cosine similarity", ge=0.0, le=1.0
    )


@api_blueprint.post(
    "/entity_similarity",
    response_model=List[NormalizedCosineSimilarity],
    tags=["entities"],
)
def entity_similarity(
    request: Request,
    sources: List[str] = Body(
        ...,
        description="A list of CURIEs corresponding to DKG terms to use as sources",
        title="source CURIEs",
        examples=[["ido:0000511", "ido:0000592", "ido:0000597", "ido:0000514"]],
    ),
    targets: Optional[List[str]] = Body(
        default=None,
        title="target CURIEs",
        description="A list of CURIEs corrsponding to DKG terms to use as targets. "
        "If not given, source CURIEs are used in all-by-all comparison",
        examples=[["ido:0000566", "ido:0000567"]],
    ),
):
    """Get normalized cosine similarities between source and target entities.

    Similarity is calculated based on topological embeddings of terms in the DKG
    produced by the Second-order LINE algorithm described in
    `LINE: Large-scale Information Network Embedding <https://arxiv.org/pdf/1503.03578>`_.
    This means that the relationships (i.e., edges) between edges are used to make nodes
    that are connected to similar nodes more similar in vector space.

    .. warning::

        The current embedding approach does **not** take into account entities'
        lexical features (labels, descriptions, and synonyms).
    """
    vectors = request.app.state.vectors
    if not vectors:
        raise HTTPException(
            status_code=500, detail="No entity vectors available"
        )
    if targets is None:
        targets = sources
    rv = []
    for source, target in itt.product(sources, targets):
        source_vector = vectors.get(source)
        if source_vector is None:
            continue
        target_vector = vectors.get(target)
        if target_vector is None:
            continue
        cosine_distance = distance.cosine(source_vector, target_vector)
        cosine_similarity = (2 - cosine_distance) / 2
        rv.append(
            NormalizedCosineSimilarity(
                source=source, target=target, similarity=cosine_similarity
            )
        )
    return rv
