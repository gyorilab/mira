# -*- coding: utf-8 -*-

"""Run the MIRA metaregistry from a custom configuration file."""

from pathlib import Path

import click
from more_click import run_app, with_gunicorn_option, workers_option

from mira.dkg.metaregistry.utils import get_app

__all__ = ["main"]


@click.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=5000, type=int, show_default=True)
@click.option("--config", type=Path, help="Path to custom metaregistry configuration.")
@click.option("--root-path", type=str, help="Set a different root path than "
                                            "the default, e.g. when running "
                                            "behind a proxy.")
@workers_option
@with_gunicorn_option
def main(
    host: str,
    port: int,
    config: Path,
    root_path: str,
    with_gunicorn: bool,
    workers: int,
):
    """Run a custom Bioregistry instance based on a MIRA DKG."""
    app = get_app(config=config, root_prefix=root_path)
    run_app(app, host=host, port=str(port), with_gunicorn=with_gunicorn, workers=workers)


if __name__ == "__main__":
    main()
