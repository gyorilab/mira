"""A custom deployment of the Bioregistry."""

from pathlib import Path

from mira.dkg.metaregistry.utils import get_app

HERE = Path(__file__).parent.resolve()
EPI_CONFIG = HERE.joinpath("epi.json")

app = get_app(EPI_CONFIG)

if __name__ == "__main__":
    app.run()
