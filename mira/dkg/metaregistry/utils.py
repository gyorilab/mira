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

from mira.dkg.models import Config

__all__ = ["get_app", "PrefixMiddleware"]


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
    config: Union[None, str, Path, Config] = None, root_prefix: str = ""
) -> Flask:
    """Get the MIRA metaregistry app."""
    if config is None:
        config_path = Path(
            os.getenv("MIRA_REGISTRY_CONFIG")
            or pystow.get_config("mira", "registry_config", raise_on_missing=True)
        )
        config = parse_config(config_path)
    elif isinstance(config, (str, Path)):
        config = parse_config(config)

    manager = Manager(registry=config.registry, collections=config.collections, contexts={})
    flask_app = bioregistry.app.impl.get_app(manager=manager, config=config.web)
    if root_prefix:
        flask_app.config["APPLICATION_ROOT"] = root_prefix
    return flask_app


class PrefixMiddleware(object):

    def __init__(self, app: Flask, prefix=''):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):

        if environ['PATH_INFO'].startswith(self.prefix):
            environ['PATH_INFO'] = environ['PATH_INFO'][len(self.prefix):]
            environ['SCRIPT_NAME'] = self.prefix
            return self.app(environ, start_response)
        else:
            start_response('404', [('Content-Type', 'text/plain')])
            return ["This url does not belong to the app.".encode()]
