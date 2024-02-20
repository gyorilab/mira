import copy
import csv
from collections import defaultdict
import logging
import math
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

from mira.sources.biomodels import get_sbml_model
from mira.sources.biomodels import template_model_from_sbml_string
from mira.metamodel import *
from mira.resources import get_resource_file


import requests
import bioregistry
import libsbml
from libsbml import SBMLReader
import sympy
from lxml import etree
from tqdm import tqdm




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
#: This XPath query gets annotations on species for their structured
#: identifiers, typically given as MIRIAM URIs or URNs
IDENTIFIERS_XPATH = f"rdf:RDF/rdf:Description/bqbiol:is/rdf:Bag/rdf:li"
COPASI_DESCR_XPATH = "/annotation/*[2]/rdf:RDF/rdf:Description"
COPASI_IS = "%s/CopasiMT:is" % COPASI_DESCR_XPATH
COPASI_IS_VERSION_OF = "%s/CopasiMT:isVersionOf" % COPASI_DESCR_XPATH
COPASI_HAS_PROPERTY = "%s/bqbiol:hasProperty" % COPASI_DESCR_XPATH
#: This is an alternative XPath for groundings that use the isVersionOf
#: relation and are thus less specific than the one above but can be used
#: as fallback
IDENTIFIERS_VERSION_XPATH = (
    f"rdf:RDF/rdf:Description/bqbiol:isVersionOf/rdf:Bag/rdf:li"
)
#: This XPath query gets annotations on species about their properties,
#: which typically help ad-hoc create subclasses that are more specific
PROPERTIES_XPATH = f"rdf:RDF/rdf:Description/bqbiol:hasProperty/rdf:Bag/rdf:li"
#: This query helps get annotations on reactions, like "this reaction is a
#: _protein-containing complex disassembly_ (GO:0043624)"
IS_VERSION_XPATH = f"rdf:RDF/rdf:Description/bqbiol:hasProperty/rdf:Bag/rdf:li"


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
        self.units = get_units(self.sbml_model.unit_definitions)

        self.extract_model()

    def extract_model(self):
        # model_id,
        if self.model_id is None:
            self.model_id = get_model_id(self.sbml_model)
        model_annots = get_model_annotations(self.sbml_model)
        reporter_ids = set(self.reporter_ids or [])
        concepts = self._extract_concepts()

        templates: List[Template] = []
        all_species = {
            species.id for species in self.qual_model_plugin.qualitative_species
        }

        # parameters and compartment attributes for sbml_model are empty, they don't exist for
        # the qual_model_plugin
        all_parameters = {
            parameter.id: {
                "value": parameter.value,
                "description": parameter.name,
                "units": self.get_object_units(parameter),
            }
            for parameter in self.sbml_model.parameters
        }

        parameter_symbols = {
            parameter.id: sympy.Symbol(parameter.id)
            for parameter in self.sbml_model.parameters
        }
        compartment_symbols = {
            compartment.id: sympy.Symbol(compartment.id)
            for compartment in self.sbml_model.compartments
        }
        # Add compartment volumes as parameters
        for compartment in self.sbml_model.compartments:
            all_parameters[compartment.id] = {
                "value": compartment.volume,
                "description": compartment.name,
                "units": self.get_object_units(compartment),
            }

        # Handle custom function definitions in the model
        function_lambdas = {}
        for fun_def in self.sbml_model.function_definitions:
            args = [
                fun_def.getArgument(i).getName()
                for i in range(fun_def.getNumArguments())
            ]
            arg_symbols = {arg: sympy.Symbol(arg) for arg in args}

            signature = tuple(arg_symbols.values())
            formula_str = get_formula_str(fun_def.getBody())
            if isinstance(formula_str, float) and math.isnan(formula_str):
                continue
            formula = safe_parse_expr(formula_str, local_dict=arg_symbols)
            lmbd = sympy.Lambda(signature, formula)
            function_lambdas[fun_def.id] = lmbd

        # In formulas, the species ID appears instead of the species name
        # and so we have to map these to symbols corresponding to the species name
        species_id_map = {
            species.id: (
                sympy.Symbol(species.name)
                if (
                    species.name
                    and "(" not in species.name
                    and "-" not in species.name
                    and "+" not in species.name
                )
                else sympy.Symbol(species.id)
            )
            for species in self.sbml_model.species
        }

        all_locals = {
            k: v
            for k, v in (
                list(parameter_symbols.items())
                + list(compartment_symbols.items())
                + list(function_lambdas.items())
                + list(species_id_map.items())
            )
        }

        # Handle custom assignment rules in the model
        assignment_rules = {}
        for rule in self.sbml_model.rules:
            rule_expr = parse_assignment_rule(rule.formula, all_locals)
            if rule_expr:
                assignment_rules[rule.id] = rule_expr

        all_implicit_modifiers = set()
        implicit_modifiers = None
        for transition in self.qual_model_plugin.transitions:
            inputs = [
                qual_species.id for qual_species in transition.getListOfInputs()
            ]
            outputs = [
                qual_species.id
                for qual_species in transition.getListOfOutputs()
            ]

            pass

    def _extract_concepts(self) -> Mapping[str, Concept]:
        concepts = {}
        for species in self.qual_model_plugin.getListOfQualitativeSpecies():
            # QualitativeSpecies doesn't have units attribute. Cannot use get_object_units method
            units = None
            concept = _extract_concept(
                species, model_id=self.model_id, units=units
            )
            concepts[species.getId()] = concept
        return concepts

    def get_object_units(self, object):
        if object.units:
            if object.units == "dimensionless":
                return Unit(expression=sympy.Integer(1))
            else:
                return Unit(expression=self.units[object.units])
        else:
            return None


def parse_assignment_rule(rule, locals):
    try:
        expr = safe_parse_expr(rule, local_dict=locals)
        return expr
    except SyntaxError:
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

    annotation_string = species.getAnnotationString()
    if not annotation_string:
        logger.debug(f"[{model_id} species:{species_id}] had no annotations")
        concept = Concept(
            name=species_name,
            display_name=display_name,
            identifiers={},
            context={},
            units=units,
        )
        return concept

    concept = Concept(
        name=species_name,
        display_name=display_name,
        identifiers={},
        context={},
        units=units,
    )
    return concept

    # namespace error when using a species' annotation string
    annotation_tree = etree.fromstring(annotation_string)


def get_model_annotations(sbml_model) -> Annotations:
    """Get the model annotations from the SBML model."""

    # sbml_model has an empty annotation string, this method doesn't exist for the qual_plugin_model
    ann_xml = sbml_model.getAnnotationString()
    if not ann_xml:
        return None
    et = etree.fromstring(ann_xml)
    # Publication: bqmodel:isDescribedBy
    # Disease: bqbiol:is
    # Taxa: bqbiol:hasTaxon
    # Model type: bqbiol:hasProperty
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


def get_formula_str(ast_node):
    name = ast_node.getName()
    if not name:
        op = ast_node.getOperatorName()
        if op:
            if op == "times":
                op_str = "*"
            elif op == "plus":
                op_str = "+"
            elif op == "divide":
                op_str = "/"
            elif op == "minus":
                op_str = "-"
            else:
                print("Unknown op: %s" % op)
                assert False
            # Special case where we have a unary minus
            if op == "minus" and ast_node.isUMinus():
                return "-%s" % get_formula_str(ast_node.getChild(0))
            # More general binary case
            return "(%s %s %s)" % (
                get_formula_str(ast_node.getChild(0)),
                op_str,
                get_formula_str(ast_node.getChild(1)),
            )
        val = ast_node.getValue()
        if val is not None:
            return val
    # Exponential doesn't show up as an operator but rather a name
    elif name in {"exp"}:
        return "%s(%s)" % (name, get_formula_str(ast_node.getChild(0)))
    else:
        return name

apoptosis_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules"
    "/Apoptosis_qual.sbml?ref_type=heads"
)
apoptosis_file_2 = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/blob/master/Executable%20Modules/model_Apoptosis.sbml?ref_type=heads"
)
drug_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/Drugs_mechanisms_qual.sbml?ref_type=heads"
)

stress_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/ER_stress_qual.sbml?ref_type=heads"
)
interferon_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/Interferon_qual.sbml?ref_type=heads"
)
pamp_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/PAMP_signaling_qual.sbml?ref_type=heads"
)
ubiquitination_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/Ubiquitination_qual.sbml?ref_type=heads"
)

virus_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/Virus_Replication_qual.sbml?ref_type=heads"
)
def test_qual_own():
    xml_string = virus_file.text
    sbml_document = SBMLReader().readSBMLFromString(xml_string)
    sbml_document.setPackageRequired("qual", True)
    model = sbml_document.getModel()
    qual_model_plugin = model.getPlugin("qual")
    processor = SbmlQualProcessor(model, qual_model_plugin)
