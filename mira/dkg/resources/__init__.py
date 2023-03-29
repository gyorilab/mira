import os
from pathlib import Path

__all__ = [
    "HERE",
    "get_resource_path",
    "SLIMS",
]

import obonet

from pyobo import Obo, from_obonet

HERE = os.path.dirname(os.path.abspath(__file__))


def get_resource_path(fname):
    """Return a full path to a given resource file name."""
    return os.path.join(HERE, fname)


def get_ncbitaxon() -> Obo:
    return from_obonet(obonet.read_obo(get_resource_path("ncbitaxon_slim.obo")))


#: A dictionary of slim (i.e. custom term subset) ontologies
SLIMS = {
    "ncit": Path(get_resource_path("ncit_slim.json")),
    "covoc": Path(get_resource_path("covoc_slim.json")),
    "efo": Path(get_resource_path("efo_slim.json")),
    "uat": Path(get_resource_path("uat.json")),
    "omit": Path(get_resource_path("omit_slim.json")),
}
