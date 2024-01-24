import random

from flask import Blueprint, render_template

from .proxies import client, grounder

__all__ = ["ui_blueprint"]

ui_blueprint = Blueprint("ui", __name__)


@ui_blueprint.route("/", methods=["GET"])
def home():
    """Render the home page."""
    node_counter = client.get_node_counter()
    node_total = sum(node_counter.values())
    return render_template(
        "home.html",
        number_terms=len(grounder.entries),
        node_counter=node_counter,
        node_total=node_total,
    )


@ui_blueprint.route("/entity/<curie>", methods=["GET"])
def view_entity(curie: str):
    """Render information about a node."""
    entity = client.get_entity(curie)
    return render_template(
        "entity.html",
        entity=entity,
    )
