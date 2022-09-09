"""Constants for the MIRA Metaregistry."""

import itertools as itt
import json
import os
from pathlib import Path
from typing import Optional, Set

import bioregistry
import bioregistry.app.impl
import pystow
from bioregistry import Manager
from flask import Flask

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


def get_app(
    *,
    neo4j_url: Optional[str] = None,
    neo4j_user: Optional[str] = None,
    neo4j_password: Optional[str] = None,
    config_path: Optional[Path] = None,
) -> Flask:
    """Get the MIRA metaregistry app."""
    if not config_path:
        config_path = os.getenv("MIRA_REGISTRY_CONFIG") or pystow.get_config(
            "mira", "registry_config", raise_on_missing=True
        )

    config = json.loads(config_path.read_text())
    prefixes = get_prefixes(
        neo4j_url=neo4j_url, neo4j_user=neo4j_user, neo4j_password=neo4j_password
    )
    slim_registry = {
        resource.prefix: resource
        for resource in bioregistry.resources()
        if resource.prefix in prefixes
    }
    manager = Manager(registry=slim_registry, collections={}, contexts={})
    return bioregistry.app.impl.get_app(manager=manager, config=config)
