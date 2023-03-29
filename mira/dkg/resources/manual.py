import obonet

from pathlib import Path
from pyobo.reader import from_obonet
from pyobo import Obo

__all__ = [
    "PATH",
    "get_manual",
]

HERE = Path(__file__).parent.resolve()
PATH = HERE.joinpath("manual.obo")


def get_manual() -> Obo:
    return from_obonet(obonet.read_obo(PATH))
