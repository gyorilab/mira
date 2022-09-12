"""Constants for the MIRA Metaregistry."""

import json
import os
from pathlib import Path
from typing import Union

import bioregistry
import bioregistry.app.impl
import pystow
from bioregistry import Collection, Manager, Resource
from flask import Flask

from mira.dkg.construct import METAREGISTRY_PATH
from mira.dkg.construct_registry import Config

__all__ = ["get_app"]


def parse_config(path: Path) -> Config:
    k = json.loads(path.read_text())
    return Config(
        web=k["web"],
        registry={
            prefix: Resource(prefix=prefix, **value) for prefix, value in k["registry"].items()
        },
        collections={
            collection: Collection(**data) for collection, data in k.get("collections", {})
        },
    )


def get_app(
    config: Union[None, str, Path, Config] = None,
) -> Flask:
    """Get the MIRA metaregistry app."""
    if config is None:
        config_path = Path(
            os.getenv("MIRA_REGISTRY_CONFIG")
            or pystow.get_config("mira", "registry_config")
            or METAREGISTRY_PATH
        )
        config = parse_config(config_path)
    elif isinstance(config, (str, Path)):
        config = parse_config(config)

    manager = Manager(registry=config.registry, collections=config.collections, contexts={})
    return bioregistry.app.impl.get_app(manager=manager, config=config.web)
