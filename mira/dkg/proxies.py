"""Proxies for the MIRA app."""

from flask import current_app
from werkzeug.local import LocalProxy

from .client import Neo4jClient
from .utils import MiraState

__all__ = [
    "mira_state",
    "grounder",
    "client",
]

mira_state: MiraState = LocalProxy(lambda: current_app.config["mira"])
grounder = LocalProxy(lambda: mira_state.grounder)
client: Neo4jClient = LocalProxy(lambda: mira_state.client)
