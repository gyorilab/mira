# -*- coding: utf-8 -*-

"""Run the MIRA metaregistry from a custom configuration file."""

from pathlib import Path
from typing import Optional

import click
from more_click import run_app, with_gunicorn_option, workers_option

from mira.dkg.metaregistry.utils import get_app

__all__ = ["main"]


@click.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=5000, type=int, show_default=True)
@click.option("--neo4j-url")
@click.option("--neo4j-user")
@click.option("--neo4j-password")
@click.option("--config", type=Path, required=True)
@workers_option
@with_gunicorn_option
def main(
    host: str,
    port: int,
    config: Path,
    with_gunicorn: bool,
    workers: int,
    neo4j_url: Optional[str],
    neo4j_user: Optional[str],
    neo4j_password: Optional[str],
):
    """Run a custom Bioregistry instance based on a MIRA DKG.

    Requires configuration for MIRA connection.
    """
    app = get_app(
        config_path=config,
        neo4j_url=neo4j_url,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
    )
    run_app(app, host=host, port=port, with_gunicorn=with_gunicorn, workers=workers)


if __name__ == "__main__":
    main()
