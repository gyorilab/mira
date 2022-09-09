"""Constants for the MIRA Metaregistry."""

import itertools as itt
import json
import os
from collections import ChainMap
from pathlib import Path
from typing import Any, Mapping, Optional, Set, Union

import bioregistry
import bioregistry.app.impl
import pystow
from bioregistry import Collection, Manager, Resource
from flask import Flask
from pydantic import BaseModel, Field

from mira.dkg.client import Neo4jClient

__all__ = ["get_app"]

COLLECTIONS = {
    "0000007",  # publishing
    "0000008",  # ASKEM custom list, see https://bioregistry.io/collection/0000008
}


def get_prefixes(
    *,
    neo4j_url: Optional[str] = None,
    neo4j_user: Optional[str] = None,
    neo4j_password: Optional[str] = None,
) -> Set[str]:
    """Get the prefixes to use for the slim."""
    client = Neo4jClient(url=neo4j_url, user=neo4j_user, password=neo4j_password)

    # Get all prefixes covered by the nodes in the domain knowledge graph
    node_prefixes = client.get_node_counter()

    # Get all prefixes covered by the relations in the domain knowlege graph
    edge_curies = client.query_tx("MATCH ()-[r]->() RETURN DISTINCT r.pred")
    if edge_curies is None:
        raise RuntimeError("could not run query")
    edge_prefixes = {edge_curie.split(":")[0] for edge_curie, in edge_curies}

    bioregistry_prefixes = {
        resource.prefix for resource in bioregistry.resources() if "bioregistry" in resource.prefix
    }

    collection_prefixes = {
        prefix
        for collection_id in COLLECTIONS
        for prefix in bioregistry.get_collection(collection_id).resources
    }

    return set(
        itt.chain(
            node_prefixes,
            edge_prefixes,
            bioregistry_prefixes,
            collection_prefixes,
        )
    )


class Config(BaseModel):
    """Configuration for a custom metaregistry instance."""

    web: Mapping[str, Any] = Field(
        default_factory=dict, description="Configuration for the web application"
    )
    registry: Mapping[str, Resource] = Field(
        default_factory=dict, description="Custom registry entries"
    )
    collections: Mapping[str, Collection] = Field(
        default_factory=dict, description="Custom collections"
    )


def get_app(
    *,
    neo4j_url: Optional[str] = None,
    neo4j_user: Optional[str] = None,
    neo4j_password: Optional[str] = None,
    config: Union[None, str, Path, Config] = None,
) -> Flask:
    """Get the MIRA metaregistry app."""
    if config is None:
        config_path = Path(
            os.getenv("MIRA_REGISTRY_CONFIG")
            or pystow.get_config("mira", "registry_config", raise_on_missing=True)
        )
        config = Config.parse_file(config_path)
    elif isinstance(config, (str, Path)):
        config = Config.parse_file(config)

    prefixes = get_prefixes(
        neo4j_url=neo4j_url, neo4j_user=neo4j_user, neo4j_password=neo4j_password
    )
    registry = ChainMap(
        dict(config.registry),
        {
            resource.prefix: resource
            for resource in bioregistry.resources()
            if resource.prefix in prefixes
        },
    )
    manager = Manager(registry=registry, collections=config.collections, contexts={})
    return bioregistry.app.impl.get_app(manager=manager, config=config.web)
