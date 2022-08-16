"""Utilities and constants for the MIRA app."""

from dataclasses import dataclass

from gilda.grounder import Grounder

from mira.dkg.client import Neo4jClient

__all__ = [
    "MiraState",
    "PREFIXES",
]


@dataclass
class MiraState:
    """All of the state associated with the MIRA app."""

    client: Neo4jClient
    grounder: Grounder


PREFIXES = [
    "hp",
    # "genepio",
    # "disdriv", # only a few relations
    "symp",
    "ido",
    "vo",
    "ovae",
    "oae",
    # "cido",  # creates some problems on import from delimiters
    "trans",
    "doid",
    "oboinowl",
    "caro",
]
