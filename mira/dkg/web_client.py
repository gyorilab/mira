import os
from typing import Optional, Literal, Dict, Any, List, Union

import pystow
import requests

from mira.dkg.utils import DKG_REFINER_RELS
from mira.dkg import api


__all__ = [
    "get_relations_web",
    "is_ontological_child",
]


def web_client(
    endpoint: str,
    method: Literal["get", "post"],
    query_json: Optional[Dict[str, Any]] = None,  # Required for post
    api_url: Optional[str] = None,
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """A wrapper for sending requests to the REST API and returning the

    Parameters
    ----------
    endpoint :
        The endpoint to send the request to.
    method :
        Which method to use. Must be one of 'post' and 'get'.
    query_json :
        The data to send with the request. Must be filled if method is 'post'.
    api_url :
        Provide the base URL to the REST API. Use this argument to override
        the default set in MIRA_REST_URL or rest_url from the config file.

    Returns
    -------
    :
        The data sent back from the endpoint as a json
    """
    base_url = api_url or os.environ.get("MIRA_REST_URL") or pystow.get_config("mira", "rest_url")

    if not base_url:
        raise ValueError(
            "The base url for the rest api needs to either be set in the "
            "environment using the variable 'MIRA_REST_URL', be set in the "
            "pystow config 'mira'->'rest_url' or by passing it the 'api_url' "
            "parameter to this function."
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
        raise ValueError("method must be one of 'get' and 'post'")

    res.raise_for_status()

    return res.json()


def get_relations_web(
    relations_model: api.RelationQuery,
    api_url: Optional[str] = None,
):
    """A wrapper that call the rest API's get_relations endpoint

    Parameters
    ----------
    relations_model :
        An instance of a RelationQuery BaseModel
    api_url :
        Use this parameter to specify the REST API base url or to override
        the url set in the environment or the config

    Returns
    -------

    """
    query_json = relations_model.dict(exclude_unset=True, exclude_defaults=True)
    res_json = web_client(
        endpoint="/relations", method="post", query_json=query_json, api_url=api_url
    )
    # fixme: the response can also be tuple, but it looks like the api code
    #  is not done yet over there
    return [api.RelationResponse(r) for r in res_json]


def get_entity_web(curie: str, api_url: Optional[str] = None) -> Optional[api.Entity]:
    res_json = web_client(endpoint=f"/entity/{curie}", method="get", api_url=api_url)
    if res_json is not None:
        return api.Entity(**res_json)


def get_lexical_web() -> List[api.Entity]:
    pass


def is_ontological_child(child_curie: str, parent_curie: str) -> bool:
    """Check if one curie is a child term of another curie

    Parameters
    ----------
    child_curie :
        The entity, identified by its CURIE that is assumed to be a child term
    parent_curie :
        The entity, identified by its CURIE that is assumed to be a parent term

    Returns
    -------
    :
        True if the assumption that `child_curie` is an ontological child of
        `parent_curie` holds
    """
    rel_model = api.RelationQuery(
        source_curie=child_curie, relations=DKG_REFINER_RELS, target_curie=parent_curie, limit=1
    )
    res = get_relations_web(relations_model=rel_model)
    return len(res) > 0
