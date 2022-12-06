# -*- coding: utf-8 -*-

"""Run the MIRA metaregistry from a custom configuration file."""

from pathlib import Path

import click
from more_click import run_app, with_gunicorn_option, workers_option

from mira.dkg.metaregistry.utils import get_app, PrefixMiddleware

__all__ = ["main"]


@click.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=5000, type=int, show_default=True)
@click.option("--config", type=Path, help="Path to custom metaregistry configuration.")
@click.option("--root-path", type=str, required=False, default="",
              help="Set a different root path than the default, e.g. when "
                   "running behind a proxy. The root path can also be set "
                   "via the environment using 'ROOT_PATH' for use in e.g. a "
                   "docker. If both are set, the --root-path option takes "
                   "precedence over 'ROOT_PATH'.")
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
    if not root_path:
        import os
        if os.environ.get("ROOT_PATH"):
            root_path = os.environ["ROOT_PATH"]
            print(f"Using root path {root_path} from environment")
        else:
            print(f"No {root_path} set, app's root will be at '/'")
    else:
        print(f"Using root path {root_path}")
    app = get_app(config=config)
    if root_path:
        prefixed_app = PrefixMiddleware(app, prefix=root_path)
        app = prefixed_app
    run_app(app, host=host, port=str(port), with_gunicorn=with_gunicorn, workers=workers)


if __name__ == "__main__":
    main()
