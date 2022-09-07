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
    # meta
    "oboinowl",
    "owl",
    "rdfs",
    # upper level ontologies
    "bfo",
    "caro",
    # domain ontologies
    "hp",
    # "genepio",
    "disdriv",  # only a few relations
    "symp",
    "ido",
    "vo",
    "ovae",
    "oae",
    # "cido",  # creates some problems on import from delimiters
    "trans",
    "doid",
    # Fill in the gaps
    # "uberon",
    # "cl",
    # "chebi",
    # "mondo",
]


#: A list of all relation types that are considered refinement relations
DKG_REFINER_RELS = ["rdfs:subClassOf", "part_of"]
