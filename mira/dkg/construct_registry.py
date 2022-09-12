"""Constants for the MIRA Metaregistry."""

import csv
import gzip
import itertools as itt
import json
from collections import ChainMap
from pathlib import Path
from typing import Any, Mapping, Optional, Set

import bioregistry
import bioregistry.app.impl
import click
from bioregistry import Collection, Manager, Resource
from pydantic import BaseModel, Field
from tqdm import tqdm

from mira.dkg.construct import EDGES_PATH, NODES_PATH, METAREGISTRY_PATH, upload_s3

HERE = Path(__file__).parent.resolve()
EPI_CONF_PATH = HERE.joinpath("metaregistry", "epi.json")

COLLECTIONS = {
    "0000007",  # publishing
    "0000008",  # ASKEM custom list, see https://bioregistry.io/collection/0000008
}


def get_prefixes(
    *, nodes_path: Optional[Path] = None, edges_path: Optional[Path] = None
) -> Set[str]:
    """Get the prefixes to use for the slim."""
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
            get_dkg_prefixes(nodes_path=nodes_path, edges_path=edges_path),
            bioregistry_prefixes,
            collection_prefixes,
        )
    )


def get_dkg_prefixes(
    nodes_path: Optional[Path] = None, edges_path: Optional[Path] = None
) -> Set[str]:
    prefixes: Set[str] = set()

    with gzip.open(nodes_path or NODES_PATH, "rt") as file:
        reader = csv.reader(file, delimiter="\t")
        _header = next(reader)
        it = tqdm(reader, unit="node", unit_scale=True)
        for (
            curie,
            _label,
            _name,
            _synoynms,
            _obsolete,
            _type,
            _description,
            xrefs,
            _alts,
            _version,
        ) in it:
            if not curie or curie.startswith("_:geni"):
                continue
            prefix, identifier = curie.split(":", 1)
            prefixes.add(prefix)
            for xref in xrefs.split(";"):
                if xref:
                    prefixes.add(xref.split(":", 1)[0])

    with gzip.open(edges_path or EDGES_PATH, "rt") as file:
        reader = csv.reader(file, delimiter="\t")
        _header = next(reader)
        it = tqdm(reader, unit="edge", unit_scale=True)
        for s, o, _type, p, _source, _graph, _version in it:
            if s.startswith("http"):
                continue  # skip unnormalized
    return prefixes


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


@click.command()
@click.option("--config-path", type=Path, default=EPI_CONF_PATH)
@click.option("--nodes-path", type=Path, default=NODES_PATH)
@click.option("--edges-path", type=Path, default=EDGES_PATH)
@click.option("--upload", is_flag=True)
def main(config_path, nodes_path, edges_path, upload: bool):
    _construct_registry(
        config_path=config_path, nodes_path=nodes_path, edges_path=edges_path, upload=upload,
    )


def _construct_registry(
    *,
    config_path: Path,
    nodes_path: Optional[Path] = None,
    edges_path: Optional[Path] = None,
    upload: bool = False,
):
    config = Config.parse_file(config_path)

    prefixes = get_prefixes(nodes_path=nodes_path, edges_path=edges_path)
    manager = Manager(
        registry=ChainMap(
            dict(config.registry),
            {
                resource.prefix: resource
                for resource in bioregistry.resources()
                if resource.prefix in prefixes
            },
        )
    )
    new_config = Config(
        web=config.web,
        registry=manager._rasterized_registry(),
        collections=config.collections,
    )

    METAREGISTRY_PATH.write_text(
        json.dumps(new_config.dict(exclude_none=True, exclude_unset=True), indent=2)
    )
    if upload:
        upload_s3(METAREGISTRY_PATH)


if __name__ == "__main__":
    main()
