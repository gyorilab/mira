"""Neo4j client module."""

import click
import flask
from more_click import run_app, with_gunicorn_option, host_option, port_option

from .client import Neo4jClient
from .grounding import grounding_blueprint
from .utils import MiraState, PREFIXES


@click.command()
@host_option
@port_option
@with_gunicorn_option
def main(port, with_gunicorn: bool):
    app = flask.Flask(__name__)

    client = Neo4jClient()
    app.config["mira"] = MiraState(
        client=client,
        grounder=client.get_grounder(PREFIXES),
    )

    app.register_blueprint(grounding_blueprint)
    run_app(app, port=port, with_gunicorn=with_gunicorn)


if __name__ == '__main__':
    main()
