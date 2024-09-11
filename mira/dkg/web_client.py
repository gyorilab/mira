import os
from typing import Optional, Literal, Dict, Any, List, Union, Tuple, Set

import pystow
import requests

from mira.dkg import api, grounding
from mira.dkg.client import Entity, AskemEntity
from mira.dkg.utils import DKG_REFINER_RELS

__all__ = [
    "web_client",
    "get_relations_web",
    "get_entity_web",
    "get_entities_web",
    "get_lexical_web",
    "ground_web",
    "search_web",
    "get_transitive_closure_web",
    "is_ontological_child_web",
    "MissingBaseUrlError",
]


class MissingBaseUrlError(ValueError):
    """Raised when the base url for the REST API is missing"""


def web_client(
    endpoint: str,
    method: Literal["get", "post"],
    query_json: Optional[Union[Dict[str, Any], List[Tuple[str, Any]]]] = None,
    api_url: Optional[str] = None,
) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
    """A wrapper for sending requests to the REST API and returning the results

    Parameters
    ----------
    endpoint :
        The endpoint to send the request to.
    method :
        Which method to use. Must be one of 'post' and 'get'.
    query_json :
        The data to send with the request. This parameter must be filled if
        method is 'post'. If method is 'get', and the endpoint expects a
        list, this parameter needs to be a list of tuples of key-value
        pairs, i.e. [(key, value)], as per the requests api:
        https://requests.readthedocs.io/en/latest/api/#requests.get
        To provide a list for one parameter, repeat the key with each value
        of the list.

        Example:
        If the endpoint expect key1 to be a list and key2 to be parameter,
        sending [(key1, value1), (key1, value2), (key2, value3)] as
        query_json will result in the endpoint receiving the variables
        key1=[value1, value2], key2=value3
    api_url :
        Provide the base URL to the REST API. Use this argument to override
        the default set in MIRA_REST_URL or rest_url from the config file.

    Returns
    -------
    :
        The data sent back from the endpoint as a json, unless the response
        is empty, in which case None is returned.
    """
    base_url = api_url or os.environ.get("MIRA_REST_URL") or pystow.get_config("mira", "rest_url")

    if not base_url:
        raise MissingBaseUrlError(
            "The base url for the REST API needs to either be set in the "
            "environment using the variable 'MIRA_REST_URL', be set in the "
            "pystow config 'mira'->'rest_url' or by passing it the 'api_url' "
            "parameter to the web client function used."
        )

    # Clean base url and endpoint
    base_url = base_url.rstrip("/") + "/api" if not base_url.endswith("/api") else base_url
    endpoint = endpoint if endpoint.startswith("/") else "/" + endpoint
    endpoint_url = base_url + endpoint

    if method == "post":
        if query_json is None:
            raise ValueError(f"POST request to endpoint {endpoint} requires query data")
        res = requests.post(endpoint_url, json=query_json)
    elif method == "get":
        # Add query_json as params if present
        kw = dict() if query_json is None else {"params": query_json}
        res = requests.get(endpoint_url, **kw)
    else:
        raise ValueError("Method must be one of 'get' and 'post'")

    res.raise_for_status()

    return res.json()


def get_relations_web(
    relations_model: api.RelationQuery,
    api_url: Optional[str] = None,
) -> Union[List[api.RelationResponse], List[api.FullRelationResponse]]:
    """Get relations based on the query contained in the RelationQuery model

    A wrapper that call the REST API's get_relations endpoint.

    Parameters
    ----------
    relations_model :
        An instance of a RelationQuery BaseModel.
    api_url :
        Use this parameter to specify the REST API base url or to override
        the url set in the environment or the config.

    Returns
    -------
    :
        If any relation exists, a list of RelationResponse models or
        FullRelationResponse models if a full query was requested.

    Examples
    --------
    To populate the RelationQuery BaseModel, follow this example:

    .. code-block:: python

        from mira.dkg.api import RelationQuery
        from mira.dkg.web_client import get_relations_web
        relation_query = RelationQuery(target_curie="ncbitaxon:10090", relations="vo:0001243")
        relations = get_relations_web(relations_model=relation_query)
        print(relations[:5])

    """
    query_json = relations_model.model_dump(exclude_unset=True,
                                       exclude_defaults=True)
    res_json = web_client(
        endpoint="/relations", method="post", query_json=query_json, api_url=api_url
    )
    if res_json is not None:
        if relations_model.full:
            return [api.FullRelationResponse(**r) for r in res_json]
        else:
            return [api.RelationResponse(**r) for r in res_json]


def get_entity_web(curie: str, api_url: Optional[str] = None) -> Optional[api.Entity]:
    """Get information about an entity based on its compact URI (CURIE)

    A wrapper that calls the REST API's entity endpoint.

    Parameters
    ----------
    curie :
        The curie for an entity to get information about.
    api_url :
        Use this parameter to specify the REST API base url or to override
        the url set in the environment or the config.


    Returns
    -------
    :
        Returns an Entity model, if the entity exists in the graph.
    """
    res_json = web_client(endpoint=f"/entity/{curie}", method="get", api_url=api_url)
    if res_json is not None:
        return api.Entity(**res_json)


def get_entities_web(curies: List[str]) -> List[Union[AskemEntity, Entity]]:
    """Get information about multiple entities (e.g., their names,
    description synonyms, alternative identifiers, database
    cross-references, etc.) based on their respective compact URIs (CURIEs).

    A wrapper that calls the REST API's entities endpoint.

    Parameters
    ----------
    curies :
        A list of curies for entities to get information about.

    Returns
    -------
    :
        Returns a list of Entity models, if the entities exist in the graph.
    """
    # Endpoint expects '<prefix>:<local unique identifier>,...',
    # e.g.: "ido:0000511,ido:0000512"
    curies_str = ",".join(curies)
    res_json = web_client(endpoint=f"/entities/{curies_str}", method="get")
    if res_json is not None:
        return [Entity(**record) for record in res_json]


def get_lexical_web(api_url: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get lexical information for all entities in the graph

    A wrapper that calls the REST API's lexical endpoint.

    Parameters
    ----------
    api_url :
        Use this parameter to specify the REST API base url or to override
        the url set in the environment or the config.

    Returns
    -------
    :
        A list of all entities in the graph.
    """
    return web_client(endpoint="/lexical", method="get", api_url=api_url)


def ground_web(
    text: str,
    namespaces: Optional[List[str]] = None,
    api_url: Optional[str] = None,
) -> Optional[grounding.GroundResults]:
    """Ground text with Gilda to an ontology identifier

    A wrapper that calls the REST API's grounding POST endpoint

    Parameters
    ----------
    text :
        The text to be grounded.
    namespaces :
        A list of namespaces to filter groundings to. Optional. Example=["do", "mondo", "ido"]
    api_url
        Use this parameter to specify the REST API base url or to override
        the url set in the environment or the config.

    Returns
    -------
    :
        If the query results in at least one grounding, a GroundResults
        model is returned with all the results.
    """
    query_json = {"text": text}
    if namespaces is not None:
        query_json["namespaces"] = namespaces
    res_json = web_client(endpoint="/ground", method="post", query_json=query_json, api_url=api_url)
    if res_json is not None:
        return grounding.GroundResults(**res_json)


def search_web(
    term: str, limit: int = 25, offset: int = 0, api_url: Optional[str] = None
) -> List[api.Entity]:
    """Get nodes based on a search to their name/synonyms

    A wrapper that call the REST API's search endpoint

    Parameters
    ----------
    term :
        The term to search for
    limit :
        Limit the number of results to this number. Default: 25.
    offset:
        The offset for the results
    api_url :
        Use this parameter to specify the REST API base url or to override
        the url set in the environment or the config.

    Returns
    -------
    :
        A list of the matching entities.
    """
    res_json = web_client(
        endpoint="/search", method="get", query_json={"q": term, "limit": limit, "offset": offset}, api_url=api_url
    )
    return [api.Entity(**e) for e in res_json]


def get_transitive_closure_web(
        relation_types: Optional[List[str]] = None,
        api_url: Optional[str] = None
) -> Set[Tuple[str, str]]:
    """Get a transitive closure for the given relation type(s)

    Parameters
    ----------
    relation_types :
        A list of relation types to get the transitive closure for.
        Optional. Default is ["subclassof", "part_of"].
    api_url :
        Use this parameter to specify the REST API base url or to override
        the url set in the environment or the config.

    Returns
    -------
    :
        A set of tuples of CURIEs representing a transitive closure set for
        the relations of the requested type(s). The pairs are ordered as
        (successor, descendant). Note that if the relations are ones that
        point towards taxonomical parents (e.g., subclassof, part_of), then
        the pairs are interpreted as (taxonomical child, taxonomical ancestor).
    """
    if not relation_types:
        relation_types = DKG_REFINER_RELS

    res_json = web_client(
        "/transitive_closure",
        method="get",
        query_json=[("relation_types", rt) for rt in relation_types],
        api_url=api_url
    )
    return {tuple(pair) for pair in res_json}


def is_ontological_child_web(
    child_curie: str, parent_curie: str, api_url: Optional[str] = None
) -> bool:
    """Check if one curie is a child term of another curie

    Parameters
    ----------
    child_curie :
        The entity, identified by its CURIE that is assumed to be a child term
    parent_curie :
        The entity, identified by its CURIE that is assumed to be a parent term
    api_url :
        Use this parameter to specify the REST API base url or to override
        the url set in the environment or the config

    Returns
    -------
    :
        True if the assumption that `child_curie` is an ontological child of
        `parent_curie` holds
    """
    res_json = web_client(
        "/is_ontological_child",
        method="post",
        query_json={"child_curie": child_curie, "parent_curie": parent_curie},
        api_url=api_url
    )
    return res_json["is_child"]
