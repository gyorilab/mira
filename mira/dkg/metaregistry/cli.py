"""Run the MIRA metaregistry from a custom configuration file."""

import click
from pathlib import Path

from pathlib import Path

from mira.dkg.metaregistry.utils import get_app

__all__ = [
    "main"
]


@click.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=5000, type=int, show_default=True)
@click.option("--config", type=Path, required=True)
def main(host: str, port: int, config: Path):
    app = get_app(config)
    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
