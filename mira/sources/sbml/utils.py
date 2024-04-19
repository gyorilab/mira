"""
Module to define shared functionality between processing SBML and SBML Qual documents.
"""


import csv
from collections import defaultdict
from copy import deepcopy
import logging
from typing import Optional

import bioregistry
import libsbml
import sympy
from lxml import etree
from tqdm import tqdm

from mira.metamodel import *
from mira.resources import get_resource_file


class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except Exception:
            self.handleError(record)


PREFIX_MAP = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dcterms": "http://purl.org/dc/terms/",
    "vCard": "http://www.w3.org/2001/vcard-rdf/3.0#",
    "vCard4": "http://www.w3.org/2006/vcard/ns#",
    "bqbiol": "http://biomodels.net/biology-qualifiers/",
    "bqmodel": "http://biomodels.net/model-qualifiers/",
    "CopasiMT": "http://www.copasi.org/RDF/MiriamTerms#",
    "copasi": "http://www.copasi.org/static/sbml",
    "jd": "http://www.sys-bio.org/sbml",
}

RESOURCE_KEY = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"


class Converter:
    """Wrapper around a curies converter with lazy loading."""

    def __init__(self):
        self.converter = None

    def parse_uri(self, uri):
        """Parse a URI into a prefix/identifier pair."""
        if self.converter is None:
            self.converter = bioregistry.get_converter(include_prefixes=True)
        return self.converter.parse_uri(uri)

    def uri_to_curie(self, uri: str) -> Optional[str]:
        """Turn a URI into a CURIE."""
        if self.converter is None:
            self.converter = bioregistry.get_converter(include_prefixes=True)
        return self.converter.compress(uri)


converter = Converter()


def get_model_annotations(sbml_model, *, converter, logger):
    """Get the model annotations from an SBML model."""
    ann_xml = sbml_model.getAnnotationString()
    if not ann_xml:
        return None
    et = etree.fromstring(ann_xml)
    annot_structure = {
        "publications": "bqmodel:isDescribedBy",
        "diseases": "bqbiol:is",
        "taxa": "bqbiol:hasTaxon",
        "model_type": "bqbiol:hasProperty",
        "pathway": "bqbiol:isVersionOf",  # points to pathways
        # bqbiol:isPartOf used to point to pathways
        # bqbiol:occursIn used to point to pathways - might be subtle distinction with process vs. pathway
        "homolog_to": "bqbiol:isHomologTo",
        "base_model": "bqmodel:isDerivedFrom",  # derived from other biomodel
        "has_part": "bqbiol:hasPart",  # points to pathways
    }
    annotations = defaultdict(list)
    for key, path in annot_structure.items():
        full_path = f"rdf:RDF/rdf:Description/{path}/rdf:Bag/rdf:li"
        tags = et.findall(full_path, namespaces=PREFIX_MAP)
        if not tags:
            continue
        for tag in tags:
            uri = tag.attrib.get(RESOURCE_KEY)
            if not uri:
                continue
            curie = converter.uri_to_curie(uri)
            if not curie:
                continue
            annotations[key].append(curie)

    model_id = get_model_id(sbml_model, converter=converter)
    if model_id and model_id.startswith("BIOMD"):
        license = "CC0"
    else:
        license = None

    # TODO smarter split up taxon into pathogens and host organisms
    hosts = []
    pathogens = []
    for curie in annotations.get("taxa", []):
        if curie == "ncbitaxon:9606":
            hosts.append(curie)
        else:
            pathogens.append(curie)

    model_types = []
    diseases = []
    logged_curie = set()
    for curie in annotations.get("model_type", []):
        if curie.startswith("mamo:"):
            model_types.append(curie)
        elif any(
            curie.startswith(f"{disease_prefix}:")
            for disease_prefix in ["mondo", "doid", "efo"]
        ) or _curie_is_ncit_disease(curie):
            diseases.append(bioregistry.normalize_curie(curie))
        elif curie not in logged_curie:
            logged_curie.add(curie)
            logger.debug(f"unhandled model_type: {curie}")

    return Annotations(
        name=sbml_model.getModel().getName(),
        description=None,  # TODO
        license=license,
        authors=[],  # TODO,
        references=annotations.get("publications", []),
        # no time_scale, time_start, time_end, locations from biomodels
        hosts=hosts,
        pathogens=pathogens,
        diseases=diseases,
        model_types=model_types,
    )


def get_model_id(sbml_model, *, converter):
    """Get the model ID from the model annotation."""
    ann_xml = sbml_model.getAnnotationString()
    if not ann_xml:
        return None
    et = etree.fromstring(ann_xml)
    id_tags = et.findall(
        "rdf:RDF/rdf:Description/bqmodel:is/rdf:Bag/rdf:li",
        namespaces=PREFIX_MAP,
    )
    for id_tag in id_tags:
        uri = id_tag.attrib.get(RESOURCE_KEY)
        if uri:
            prefix, identifier = converter.parse_uri(uri)
            if prefix == "biomodels.db" and identifier.startswith("BIOMD"):
                return identifier
    return None


def _curie_is_ncit_disease(curie: str) -> bool:
    prefix, identifier = bioregistry.parse_curie(curie)
    if prefix != "ncit":
        return False
    try:
        import pyobo
    except ImportError:
        return False
    else:
        # return pyobo.has_ancestor("ncit", identifier, "ncit", "C2991")
        return False


def get_grounding_map():
    def parse_identifier_grounding(grounding_str):
        # Example: ido:0000511/infected population from which we want to get
        # {'ido': '0000511'}
        if not grounding_str:
            return {}
        return dict(
            tuple(grounding.split("/")[0].split(":"))
            for grounding in grounding_str.split("|")
        )

    def parse_context_grounding(grounding_str):
        # Example: disease_severity=ncit:C25269/Symptomatic|
        #          diagnosis=ncit:C113725/Undiagnosed
        # from which we want to get {'disease_severity': 'ncit:C25269',
        #                            'diagnosis': 'ncit:C113725'}
        if not grounding_str:
            return {}
        return dict(
            tuple(grounding.split("/")[0].split("="))
            for grounding in grounding_str.split("|")
        )

    fname = get_resource_file("mapped_biomodels_groundings.csv")
    mappings = {}
    with open(fname, "r") as fh:
        reader = csv.reader(fh)
        next(reader)
        for name, ids, context, model, mapped_ids, mapped_context in reader:
            mappings[(model, name)] = (
                parse_identifier_grounding(mapped_ids),
                parse_context_grounding(mapped_context),
            )

    return mappings


grounding_map = get_grounding_map()


def get_sbml_units():
    """Build up a mapping of SBML unit kinds to their names.

    This is necessary because units are given as numbers.
    """
    module_contents = dir(libsbml)
    unit_kinds = {
        var: var.split("_")[-1].lower()
        for var in module_contents
        if var.startswith("UNIT_KIND") and var != "UNIT_KIND_INVALID"
    }
    unit_kinds = {
        getattr(libsbml, var): unit_name
        for var, unit_name in unit_kinds.items()
    }
    return unit_kinds


SBML_UNITS = get_sbml_units()


def grounding_normalize(concept):
    # A common curation mistake in BioModels: mixing up IDO and NCIT identifiers
    for k, v in deepcopy(concept.identifiers).items():
        if k == "ncit" and v.startswith("000"):
            concept.identifiers.pop(k)
            concept.identifiers["ido"] = v
        elif k == "ido" and v.startswith("C"):
            concept.identifiers.pop(k)
            concept.identifiers["ncit"] = v
    # Has property acquired immunity == immune population
    if not concept.get_curie()[0] and concept.context == {
        "property": "ido:0000621"
    }:
        concept.identifiers["ido"] = "0000592"
        concept.context = {}
    elif concept.get_curie() == ("ido", "0000514") and concept.context == {
        "property": "ido:0000468"
    }:
        concept.context = {}
    # Different ways of expression immune/recovered
    elif concept.get_curie() == ("ncit", "C171133") and concept.context == {
        "property": "ido:0000621"
    }:
        concept.identifiers = {"ido": "0000592"}
        concept.context = {}
    # Different terms for dead/deceased
    elif concept.get_curie() == ("ncit", "C168970"):
        concept.identifiers = {"ncit": "C28554"}
    return concept


def get_units(unit_definitions):
    """Return units from a list of unit definition blocks."""
    units = {}
    for unit_def in unit_definitions:
        units[unit_def.id] = process_unit_definition(unit_def)
    return units


def process_unit_definition(unit_definition):
    """Process a unit definition block to extract an expression."""
    full_unit_expr = sympy.Integer(1)
    for unit in unit_definition.units:
        unit_symbol_str = SBML_UNITS[unit.kind]
        # We assume person instead of item here
        if unit_symbol_str in unit_symbol_mappings:
            unit_symbol_str = unit_symbol_mappings[unit_symbol_str]
        unit_symbol = sympy.Symbol(unit_symbol_str)
        # We do this to avoid the spurious factors in the expression
        if unit.multiplier != 1:
            unit_symbol *= unit.multiplier
        if unit.exponent != 1:
            unit_symbol **= unit.exponent
        if unit.scale != 0:
            unit_symbol *= 10**unit.scale
        full_unit_expr *= unit_symbol
    # We apply some mappings for canonical units we want to change
    # We use equals here since == in sympy is structural equality
    for k, v in unit_expression_mappings.items():
        if full_unit_expr.equals(k):
            full_unit_expr = v
    return full_unit_expr


unit_symbol_mappings = {
    "item": "person",
    "metre": "meter",
    "litre": "liter",
}
unit_expression_mappings = {
    86400.0 * sympy.Symbol("second"): sympy.Symbol("day"),
    1 / (86400.0 * sympy.Symbol("second")): 1 / sympy.Symbol("day"),
    1
    / (86400.0 * sympy.Symbol("second") * sympy.Symbol("person")): 1
    / (sympy.Symbol("day") * sympy.Symbol("person")),
    31536000.0 * sympy.Symbol("second"): sympy.Symbol("year"),
    1 / (31536000.0 * sympy.Symbol("second")): 1 / sympy.Symbol("year"),
    1
    / (31536000.0 * sympy.Symbol("second") * sympy.Symbol("person")): 1
    / (sympy.Symbol("year") * sympy.Symbol("person")),
}
