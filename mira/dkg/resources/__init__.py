import os
from pathlib import Path

__all__ = [
    "HERE",
    "get_resource_path",
    "SLIMS",
]

HERE = os.path.dirname(os.path.abspath(__file__))


def get_resource_path(fname):
    """Return a full path to a given resource file name."""
    return os.path.join(HERE, fname)


#: A dictionary of slim (i.e. custom term subset) ontologies
SLIMS = {
    "ncit": Path(get_resource_path("ncit_slim.owl")),
    "covoc": Path(get_resource_path("covoc_slim.owl")),
    "efo": Path(get_resource_path("efo_slim.owl")),
}
