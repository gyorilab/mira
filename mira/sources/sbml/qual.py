import logging
import csv
import copy
import re
from typing import List, Mapping, Optional
from copy import deepcopy

from mira.metamodel import *
from mira.resources import get_resource_file

import bioregistry
import sympy
from tqdm import tqdm
from lxml import etree
import xml.etree.ElementTree as ET
import libsbml


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


logger = logging.getLogger(__name__)
logger.addHandler(TqdmLoggingHandler())

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
DESCRIPTION_XPATH = f".//bqbiol:isDescribedBy/rdf:Bag/rdf:li"
ENCODED_XPATH = f".//bqbiol:isEncodedBy/rdf:Bag/rdf:li"


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


class SbmlQualProcessor:
    def __init__(
        self, sbml_model, qual_model_plugin, model_id=None, reporter_ids=None
    ):
        self.qual_model_plugin = qual_model_plugin
        self.sbml_model = sbml_model
        self.model_id = model_id
        self.reporter_ids = reporter_ids

        # unit_definitions is empty for sbml_model
        self.units = get_units(self.sbml_model.unit_definitions)

    def extract_model(self):
        if self.model_id is None:
            self.model_id = get_model_id(
                self.sbml_model, self.qual_model_plugin
            )
        model_annots = get_model_annotations(
            self.sbml_model, self.qual_model_plugin
        )
        reporter_ids = set(self.reporter_ids or [])
        concepts = self._extract_concepts()

        def _lookup_concepts_filtered(species_ids) -> List[Concept]:
            return [
                concepts[species_id]
                for species_id in species_ids
                if species_id not in reporter_ids
                and "cumulative" not in species_id
            ]

        templates: List[Template] = []

        # parameters and compartment attributes for sbml_model are empty, they don't exist for
        # the qual_model_plugin

        # each input to a transition can have a negative or positive sign
        # qual:sign = positive in source file indicates it controls the production of something
        # qual:sign = negative in source file indicates it controls the degradation of something
        # if both positive and negative exists, it is production process, with a list of
        # controllers from both the negative and positive side.

        # Transitions always have at least one input and one output
        # Since we always have at least one input, there will always be at least
        # 1 controller (negative or positive). Will never have a natural template
        for transition_id, transition in enumerate(
            self.qual_model_plugin.transitions
        ):
            transition_name = transition.id

            input_names = [
                qual_species.qualitative_species
                for qual_species in transition.getListOfInputs()
            ]
            output_names = [
                qual_species.qualitative_species
                for qual_species in transition.getListOfOutputs()
            ]

            # negative sign is 0, positive sign is 1 for inputs only
            # outputs do not have a sign
            # inputs will always be 0 or 1
            positive_controller_names = [
                qual_species.qualitative_species
                for qual_species in transition.getListOfInputs()
                if qual_species.getSign() == 0
            ]

            negative_controller_names = [
                qual_species.qualitative_species
                for qual_species in transition.getListOfInputs()
                if qual_species.getSign() == 1
            ]

            input_concepts = _lookup_concepts_filtered(input_names)
            output_concepts = _lookup_concepts_filtered(output_names)
            positive_controller_concepts = _lookup_concepts_filtered(
                positive_controller_names
            )
            negative_controller_concepts = _lookup_concepts_filtered(
                negative_controller_names
            )

            if (
                not positive_controller_concepts
                and not negative_controller_concepts
            ):
                if len(input_concepts) == 1 and len(output_concepts) == 0:
                    templates.append(
                        NaturalDegradation(
                            subject=input_concepts[0],
                            name=transition_id,
                            display_name=transition_name,
                        )
                    )
                elif len(input_concepts) == 0 and len(output_concepts) == 1:
                    templates.append(
                        NaturalProduction(
                            outcome=output_concepts[0],
                            name=transition_id,
                            display_name=transition_name,
                        )
                    )
                elif len(input_concepts) == 1 and len(output_concepts) == 1:
                    templates.append(
                        NaturalConversion(
                            subject=input_concepts[0],
                            outcome=output_concepts[0],
                            name=transition_id,
                            display_name=transition_name,
                        )
                    )
            else:
                if (
                    len(positive_controller_concepts) >= 1
                    and len(negative_controller_concepts) == 0
                ):
                    if len(positive_controller_concepts) == 1:
                        templates.append(
                            ControlledProduction(
                                controller=positive_controller_concepts[0],
                                outcome=output_concepts[0],
                                name=transition_id,
                                display_name=transition_name,
                            )
                        )
                    else:
                        templates.append(
                            GroupedControlledProduction(
                                controllers=positive_controller_concepts,
                                outcome=output_concepts[0],
                                name=transition_id,
                                display_name=transition_name,
                            )
                        )
                elif (
                    len(positive_controller_concepts) == 0
                    and len(negative_controller_concepts) >= 1
                ):
                    if len(negative_controller_concepts) == 1:
                        templates.append(
                            ControlledDegradation(
                                controller=negative_controller_concepts[0],
                                subject=input_concepts[0],
                                name=transition_id,
                                display_name=transition_name,
                            )
                        )
                    else:
                        templates.append(
                            GroupedControlledDegradation(
                                controllers=negative_controller_concepts,
                                subject=input_concepts[0],
                                name=transition_id,
                                display_name=transition_name,
                            )
                        )
                elif (
                    len(positive_controller_concepts) >= 1
                    and len(negative_controller_concepts) >= 1
                ):
                    templates.append(
                        GroupedControlledProduction(
                            controllers=positive_controller_concepts
                            + negative_controller_concepts,
                            outcome=output_concepts[0],
                            name=transition_id,
                            display_name=transition_name,
                        )
                    )

        initials = {}
        for qual_species in self.qual_model_plugin.qualitative_species:
            initials[qual_species.name] = Initial(
                concept=concepts[qual_species.id],
                expression=qual_species.level,
            )

        template_model = TemplateModel(
            templates=templates, initials=initials, annotations=model_annots
        )
        return template_model

    def _extract_concepts(self) -> Mapping[str, Concept]:
        concepts = {}
        for species in self.qual_model_plugin.getListOfQualitativeSpecies():
            units = self.get_object_units(species)
            concept = _extract_concept(
                species, model_id=self.model_id, units=units
            )
            concepts[species.getId()] = concept
        return concepts

    def get_object_units(self, object):
        # QualitativeSpecies object does not have units attribute
        if hasattr(object, "units"):
            if object.units == "dimensionless":
                return Unit(expression=sympy.Integer(1))
            else:
                return Unit(expression=self.units[object.units])
        else:
            return None


def _extract_concept(species, units=None, model_id=None):
    species_id = species.getId()
    species_name = species.getName()
    display_name = species_name

    if (model_id, species_name) in grounding_map:
        mapped_ids, mapped_context = grounding_map[(model_id, species_name)]
        concept = Concept(
            name=species_name,
            display_name=display_name,
            identifiers=copy.deepcopy(mapped_ids),
            context=copy.deepcopy(mapped_context),
            units=units,
        )
        return concept
    else:
        logger.debug(
            f"[{model_id} species:{species_id}] not found in grounding map"
        )

    old_annotation_string = species.getAnnotationString()

    # current annotation misses a namespace for the rdf tag and cannot be used to create an etree
    # we add a new tag arbitrarily named "element" and add a namespace to create valid xml
    # such that it can be parsed by the etree.fromstring() method
    new_annotation_string = (
        """<element xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#" 
    xmlns:dcterms="http://purl.org/dc/terms/" xmlns:vCard="http://www.w3.org/2001/vcard-rdf/3.0#" xmlns:vCard4="http://www.w3.org/2006/vcard/ns#" xmlns:bqbiol="http://biomodels.net/biology-qualifiers/" xmlns:bqmodel="http://biomodels.net/model-qualifiers/">"""
        + old_annotation_string
        + "</element>"
    )

    if not old_annotation_string:
        logger.debug(f"[{model_id} species:{species_id}] had no annotations")
        concept = Concept(
            name=species_name,
            display_name=display_name,
            identifiers={},
            context={},
            units=units,
        )
        return concept

    annotation_tree = etree.fromstring(new_annotation_string)

    # Instead of URIs found in regular SBML, the resources found in the annotation strings for
    # these qualitative species are already in CURIE format

    description_strings = [
        desc.attrib[RESOURCE_KEY]
        for desc in annotation_tree.findall(
            DESCRIPTION_XPATH, namespaces=PREFIX_MAP
        )
    ]

    encoded_strings = [
        desc.attrib[RESOURCE_KEY]
        for desc in annotation_tree.findall(
            ENCODED_XPATH, namespaces=PREFIX_MAP
        )
    ]

    description_curies_list, encoded_curies_list = [], []

    # identifiers, typically given as MIRIAM URIs or URNs
    # remove URNs, meta-prefixes and extract only prefixes and identifiers in tuple format
    # for descriptions and encodings strings for a qualitative species
    for description_annotation in description_strings:
        if "miriam" and "hgnc.symbol" in description_annotation:
            pattern = r"hgnc\.symbol:(.*)"
            match = re.search(pattern, description_annotation)
            curie = ("hgnc", match.group(1))
            description_curies_list.append(curie)
        elif "miriam" in description_annotation:
            pattern = r":([^:]+):([^:]+)$"
            match = re.search(pattern, description_annotation)
            curie = tuple(match.groups())
            description_curies_list.append(curie)

    for encoded_annotation in encoded_strings:
        if "miriam" and "hgnc.symbol" in encoded_annotation:
            pattern = r"hgnc\.symbol:(.*)"
            match = re.search(pattern, encoded_annotation)
            curie = ("hgnc", match.group(1))
            encoded_curies_list.append(curie)
        elif "miriam" in encoded_annotation:
            pattern = r":([^:]+):([^:]+)$"
            match = re.search(pattern, encoded_annotation)
            curie = tuple(match.groups())
            encoded_curies_list.append(curie)

    context = {}

    if ("ido", "C101887") in encoded_curies_list:
        encoded_curies_list.remove(("ido", "C101887"))
        encoded_curies_list.append(("ncit", "C101887"))
    if ("ncit", "C171133") in encoded_curies_list:
        encoded_curies_list.remove(("ncit", "C171133"))
        # Reclassify asymptomatic as a disease status
    if ("ido", "0000569") in encoded_curies_list and (
        "ido",
        "0000511",
    ) in encoded_curies_list:
        encoded_curies_list.remove(("ido", "0000569"))
        context["disease_status"] = "ncit:C3833"
        # Exposed shouldn't be susceptible
    if ("ido", "0000514") in encoded_curies_list and (
        "ido",
        "0000597",
    ) in encoded_curies_list:
        encoded_curies_list.remove(("ido", "0000514"))
        # Break apoart hospitalized and ICU
    if ("ncit", "C25179") in encoded_curies_list and (
        "ncit",
        "C53511",
    ) in encoded_curies_list:
        encoded_curies_list.remove(("ncit", "C53511"))
        context["disease_status"] = "ncit:C53511"
        # Remove redundant term for deceased due to disease progression
    if ("ncit", "C28554") in encoded_curies_list and (
        "ncit",
        "C168970",
    ) in encoded_curies_list:
        encoded_curies_list.remove(("ncit", "C168970"))

    encodings = dict(encoded_curies_list)

    for idx, description_property in enumerate(sorted(description_curies_list)):
        if description_property[0] == "ncit" and description_property[
            1
        ].startswith("000"):
            prop = ("ido", description_property[1])
        elif description_property[0] == "ido" and description_property[
            1
        ].startswith("C"):
            prop = ("ncit", description_property[1])
        else:
            prop = description_property
        context[f'property{"" if idx == 0 else idx}'] = ":".join(prop)

    concept = Concept(
        name=species_name or species_id,
        display_name=display_name,
        identifiers=encodings,
        context=context,
        units=units,
    )
    concept = grounding_normalize(concept)
    return concept


# qual_model doesn't have any attribute or method to retrieve annotation. sbml_model annotation
# is an empty string
def get_model_annotations(sbml_model, qual_model):
    """Get the model annotations from the SBML qual model."""
    ann_xml = sbml_model.getAnnotationString()
    if not ann_xml:
        return None


# qual_model doesn't have any attribute or method to retrieve annotation. sbml_model annotation
# is an empty string
def get_model_id(sbml_model, qual_model):
    """Get the model ID from the SBML qual model annotation."""
    ann_xml = sbml_model.getAnnotationString()
    if not ann_xml:
        return None


def get_units(unit_definitions):
    """Return units from a list of unit definition blocks."""
    units = {}
    for unit_def in unit_definitions:
        units[unit_def.id] = process_unit_definition(unit_def)
    return units


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


def _get_grounding_map():
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


grounding_map = _get_grounding_map()


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
