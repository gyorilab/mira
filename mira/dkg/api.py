"""API endpoints."""

from flask import Blueprint, jsonify

from .proxies import client

__all__ = [
    "api_blueprint",
]

api_blueprint = Blueprint("api", __name__)


@api_blueprint.route("/parents/<curie>")
def get_parents(curie):
    """Get parents."""
    parents = client.get_parents(curie)
    return jsonify(parents)
