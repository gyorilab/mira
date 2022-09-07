import os
from typing import Optional, Union, List, Literal, Dict, Any

import pystow
import requests


def web_client(query_json: Dict[str, Any], endpoint: str, api_url: Optional[str] = None):
    """A wrapper for sending requests to the REST API"""
    # Todo: extend this function to take BaseModels from mira.dkg.api for
    #  validation as well as checking that the endpoint_url exists
    base_url = api_url or os.environ.get("MIRA_REST_URL") or pystow.get_config("mira", "rest_url")

    if not base_url:
        raise ValueError(
            "The base url for the rest api needs to either be set in the "
            "environment using the variable 'MIRA_REST_URL', be set in the "
            "pystow config 'mira'->'rest_url' or by passing it the 'api_url' "
            "parameter to this function."
        )

    base_url = base_url + "/api" if not base_url.endswith("/api") else base_url

    endpoint_url = base_url + endpoint
    res = requests.post(endpoint_url, json=query_json)
    res.raise_for_status()

    return res.json()


def get_relations_web(
    source_type: Optional[str] = None,
    source_curie: Optional[str] = None,
    target_type: Optional[str] = None,
    target_curie: Optional[str] = None,
    # "relations" is "relation_type" in client.query_relations
    relations: Union[None, str, List[str]] = None,
    relation_direction: Literal["right", "left", "both"] = "right",
    relation_min_hops: int = 1,
    relation_max_hops: int = 1,
    limit: Optional[int] = None,
    full: bool = False,
    distinct: bool = False,
    api_url: str = None,
):
    """A wrapper that call the rest API's get_relations endpoint

    Parameters
    ----------
    source_type :
        The source type (i.e., prefix). Example: "vo".
    source_curie :
        The source compact URI (CURIE). example="doid:946".
    target_type :
        "The target type (i.e., prefix)", example="ncbitaxon"
    target_curie :
        "The target compact URI (CURIE)", example="ncbitaxon:10090"
    relations :
        "A relation string or list of relation strings", example="vo:0001243"
    relation_direction :
        "The direction of the relationship". Options are "left", "right" and "both". Default: "right".
    relation_min_hops :
        "The minimum number of relationships between the subject and
        object.". Default: 1.
    relation_max_hops :
        The maximum number of relationships between the subject and object.
        Set to 0 to make infinite. Default: 1
    limit :
        A limit on the number of records returned. Example=50. Default: no
        limit.
    full :
        A flag to turn on full entity and relation metadata return. Warning, this gets pretty verbose. Default: False.
    distinct :
        A flag to turn on the DISTINCT flag in the return of a cypher query. Default: False
    api_url :
        Use this parameter to specify the REST API base url or to override
        the url set

    Returns
    -------

    """
    query_json = {
        "source_type": source_type,
        "source_curie": source_curie,
        "relations": relations,
        "relation_direction": relation_direction,
        "relation_min_hops": relation_min_hops,
        "relation_max_hops": relation_max_hops,
        "target_type": target_type,
        "target_curie": target_curie,
        "full": full,
        "distinct": distinct,
        "limit": limit,
    }
    return web_client(query_json=query_json, endpoint="/relations", api_url=api_url)


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
    dkg_refiner_rels = ["rdfs:subClassOf", "part_of"]
    res = get_relations_web(
        source_curie=child_curie, relations=dkg_refiner_rels, target_curie=parent_curie
    )
    return len(res) > 0
