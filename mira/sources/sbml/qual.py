import logging
import csv
import copy
import re
from typing import List, Mapping, Optional
from copy import deepcopy
from collections import defaultdict
from urllib.parse import unquote

from mira.metamodel import *
from mira.resources import get_resource_file

import bioregistry
import sympy
import libsbml
from tqdm import tqdm
from lxml import etree


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
        # unit_definitions,parameters, and compartment attributes are empty for an sbml_model that
        # comes from a qual plugin

        self.qual_model_plugin = qual_model_plugin
        self.sbml_model = sbml_model
        self.model_id = model_id
        self.reporter_ids = reporter_ids

    def extract_model(self):
        if self.model_id is None:
            self.model_id = get_model_id(self.sbml_model)
        model_annots = get_model_annotations(self.sbml_model)
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

        # each input to a transition can have a negative or positive sign or no sign
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

            # positive sign is 0, negative sign is 1 for inputs only
            # outputs do not have a sign
            positive_controller_names = [
                qual_species.qualitative_species
                for qual_species in transition.getListOfInputs()
                if qual_species.getSign() != 1
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
            initials[qual_species.id] = Initial(
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
            concepts[species.id] = concept
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
    # retrieve local name for species that is only used a reference in the sbml qual model
    local_qual_name_reference = species.id
    # retrieve name of the species that can be used for look up in external resources
    external_name = species.name

    if (model_id, external_name) in grounding_map:
        mapped_ids, mapped_context = grounding_map[(model_id, external_name)]
        concept = Concept(
            name=local_qual_name_reference,
            display_name=external_name,
            identifiers=copy.deepcopy(mapped_ids),
            context=copy.deepcopy(mapped_context),
            units=units,
        )
        return concept
    else:
        logger.debug(
            f"[{model_id} species:{external_name}] not found in grounding map"
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
        logger.debug(f"[{model_id} species:{external_name}] had no annotations")
        concept = Concept(
            name=local_qual_name_reference,
            display_name=external_name,
            identifiers={},
            context={},
            units=units,
        )
        return concept

    annotation_tree = etree.fromstring(new_annotation_string)

    # Instead of URIs found in regular SBML, the resources found in the annotation strings for
    # these qualitative species are already in CURIE format with the "urn" prefix and meta prefix
    # attached. We remove the "urn" identifier and metaprefix later

    description_strings_list = [
        desc.attrib[RESOURCE_KEY]
        for desc in annotation_tree.findall(
            DESCRIPTION_XPATH, namespaces=PREFIX_MAP
        )
    ]

    encoded_strings_list = [
        desc.attrib[RESOURCE_KEY]
        for desc in annotation_tree.findall(
            ENCODED_XPATH, namespaces=PREFIX_MAP
        )
    ]

    identifiers_curie_list, encoded_curies_list = [], []

    # identifiers, typically given as MIRIAM URIs or URNs
    # remove URNs, meta-prefixes and extract only prefixes and identifiers in tuple format
    # for descriptions and encodings strings for a qualitative species
    for description_string in description_strings_list:
        # remove url quoting
        description_string = unquote(description_string)

        # for resources in the format of urn:{metaprefix}:hgnc.symbol:{identifier}
        if "miriam" and "hgnc.symbol" in description_string:
            pattern = r"hgnc\.symbol:(.*)"
            match = re.search(pattern, description_string)
            curie = ("hgnc", match.group(1))
            identifiers_curie_list.append(curie)

        # for all other resources
        elif "miriam" in description_string:
            pattern = r":([^:]+):([^:]+)$"
            match = re.search(pattern, description_string)
            curie = tuple(match.groups())
            identifiers_curie_list.append(curie)

    for encoded_string in encoded_strings_list:
        encoded_string = unquote(encoded_string)
        if "miriam" and "hgnc.symbol" in encoded_string:
            pattern = r"hgnc\.symbol:(.*)"
            match = re.search(pattern, encoded_string)
            curie = ("hgnc", match.group(1))
            encoded_curies_list.append(curie)

        elif "miriam" in encoded_string:
            pattern = r":([^:]+):([^:]+)$"
            match = re.search(pattern, encoded_string)
            curie = tuple(match.groups())
            encoded_curies_list.append(curie)

    context = {}

    if ("ido", "C101887") in identifiers_curie_list:
        identifiers_curie_list.remove(("ido", "C101887"))
        identifiers_curie_list.append(("ncit", "C101887"))
    if ("ncit", "C171133") in identifiers_curie_list:
        identifiers_curie_list.remove(("ncit", "C171133"))
    # Reclassify asymptomatic as a disease status
    if ("ido", "0000569") in identifiers_curie_list and (
        "ido",
        "0000511",
    ) in identifiers_curie_list:
        identifiers_curie_list.remove(("ido", "0000569"))
        context["disease_status"] = "ncit:C3833"
    # Exposed shouldn't be susceptible
    if ("ido", "0000514") in identifiers_curie_list and (
        "ido",
        "0000597",
    ) in identifiers_curie_list:
        identifiers_curie_list.remove(("ido", "0000514"))
    # Break apart hospitalized and ICU
    if ("ncit", "C25179") in identifiers_curie_list and (
        "ncit",
        "C53511",
    ) in identifiers_curie_list:
        identifiers_curie_list.remove(("ncit", "C53511"))
        context["disease_status"] = "ncit:C53511"
    # Remove redundant term for deceased due to disease progression
    if ("ncit", "C28554") in identifiers_curie_list and (
        "ncit",
        "C168970",
    ) in identifiers_curie_list:
        identifiers_curie_list.remove(("ncit", "C168970"))

    # Multiple semantically identical CURIEs with different prefixes associated with a species.
    # Additionally, some species involve multiple agents and thus contain CURIEs for all agents
    # involved. Deterministically choose the CURIE to use as the identifier for the concept by
    # sorting the keys of the identifiers dictionary (prefix) alphabetically

    all_identifiers = dict(sorted(dict(identifiers_curie_list).items()))

    if all_identifiers:
        chosen_key = next(iter(all_identifiers))
        identifiers = {chosen_key: all_identifiers[chosen_key]}
    else:
        identifiers = {}

    # we capture context using the encoding curies as a set of generic properties
    for idx, description_property in enumerate(sorted(encoded_curies_list)):
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
        name=local_qual_name_reference,
        display_name=external_name,
        identifiers=identifiers,
        context=context,
        units=units,
    )
    concept = grounding_normalize(concept)
    return concept


def get_model_annotations(sbml_model):
    """Get the model annotations from the SBML qual model."""
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

    model_id = get_model_id(sbml_model)
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


def get_model_id(sbml_model):
    """Get the model ID from the SBML model annotation."""
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