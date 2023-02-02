"""Utilities and constants for the MIRA app."""

from dataclasses import dataclass
from typing import List

from gilda.grounder import Grounder

from mira.dkg.client import Neo4jClient, Entity
from mira.metamodel.templates import RefinementClosure

__all__ = [
    "MiraState",
    "PREFIXES",
    "DKG_REFINER_RELS",
]


@dataclass
class MiraState:
    """All of the state associated with the MIRA app."""

    client: Neo4jClient
    grounder: Grounder
    refinement_closure: RefinementClosure
    lexical_dump: List[Entity]


#: A list of all prefixes used in MIRA
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
    "trans",
    "doid",
    "apollosv",
    "efo",  # from slim
    "ncit",  # from slim
    # disease/phenomena-specific ontologies
    "cemo",
    "vido",
    "cido",
    "idocovid19",
    "idomal",  # malaria
    "vsmo",  # vector surveillance and management
    "covoc",  # from slim
    # Fill in the gaps
    # "uberon",
    # "cl",
    # "chebi",
    # "mondo",
    # Domain specific
    "probonto",
]

#: A list of all relation types that are considered refinement relations
DKG_REFINER_RELS = ["subclassof", "part_of"]
