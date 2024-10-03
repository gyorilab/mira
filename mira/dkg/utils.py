"""Utilities and constants for the MIRA app."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
from gilda.grounder import Grounder

from mira.dkg.client import Entity, Neo4jClient
from mira.metamodel import RefinementClosure

__all__ = [
    "MiraState",
    "PREFIXES",
    "DKG_REFINER_RELS",
    "DOCKER_FILES_ROOT",
]


@dataclass
class MiraState:
    """Represents the state associated with the MIRA app."""

    client: Neo4jClient
    grounder: Grounder
    refinement_closure: RefinementClosure
    lexical_dump: List[Entity]
    vectors: Dict[str, np.array]


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
    #
    "geonames",
]

#: A list of all relation types that are considered refinement relations
DKG_REFINER_RELS = ["rdfs:subclassof", "subclassof", "part_of"]

#: The root path of the MIRA app when running in a container
DOCKER_FILES_ROOT = Path("/sw")
