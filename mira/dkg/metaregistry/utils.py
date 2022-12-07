"""Constants for the MIRA Metaregistry."""

import json
import os
from pathlib import Path
from typing import Union

import bioregistry
import bioregistry.app.impl
import pystow
from bioregistry import Collection, Manager, Resource
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from flask import Flask

from mira.dkg.models import Config

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


def simple(env, resp):
    """A simple mock root endpoint to mount another flask app to"""
    resp('200 OK', [('Content-Type', 'text/plain')])
    return [b'Metaregistry root']


def get_app(
    config: Union[None, str, Path, Config] = None, root_path: str = ""
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

    manager = Manager(
        registry=config.registry, collections=config.collections, contexts={}
    )
    app = bioregistry.app.impl.get_app(manager=manager, config=config.web)
    if root_path:
        # Set basePath for swagger to know where to send example requests
        if app.swag.template is None:
            app.swag.template = {}
        app.swag.template["basePath"] = root_path

        # Follows
        # https://stackoverflow.com/a/18967744/10478812 and
        # https://gist.github.com/svieira/3434cbcaf627e50a4808
        app.config['APPLICATION_ROOT'] = root_path
        # 'simple' becomes the root and the actual app is served at root_path
        app.wsgi_app = DispatcherMiddleware(simple,
                                            mounts={root_path: app.wsgi_app})

    return app
