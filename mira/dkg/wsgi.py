"""Neo4j client module."""

import random
from dataclasses import dataclass

import click
import flask
from flask import Blueprint, request
from gilda.grounder import Grounder

from .client import Neo4jClient
from .grounding import grounding_blueprint
from .utils import PREFIXES, MiraState
from more_click import run_app, port_option, with_gunicorn_option
import click
import pystow


@click.command()
@click.option("--port", default="8771")
@click.option("--bolt-port", default="8770")  # normally this is 7687
@click.option("--bolt-host", default="localhost")
@with_gunicorn_option
def main(port, bolt_port, bolt_host, with_gunicorn: bool):
    app = flask.Flask(__name__)

    client = Neo4jClient(url=f"bolt://{bolt_host}:{bolt_port}")
    app.config["mira"] = MiraState(
        client=client,
        grounder=client.get_grounder(PREFIXES),
    )

    app.register_blueprint(grounding_blueprint)
    run_app(app, port=port, with_gunicorn=with_gunicorn)


if __name__ == '__main__':
    main()
