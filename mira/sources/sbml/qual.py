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
from libsbml import formulaToL3String
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


class SbmlQualProcessor:
    def __init__(
        self, sbml_model, qual_model_plugin, model_id=None, reporter_ids=None
    ):
        self.qual_model_plugin = qual_model_plugin
        self.sbml_model = sbml_model
        self.model_id = model_id
        self.reporter_ids = reporter_ids

        # unit_definitions is empty for sbml_model
        # self.units = get_units(self.sbml_model.unit_definitions)
        self.units = {}

        self.extract_model()

        pass

    def extract_model(self):
        # model_id,
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
        all_species = {
            species.name
            for species in self.qual_model_plugin.qualitative_species
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

        all_implicit_modifiers = set()
        implicit_modifiers = None
        for idx, transition in enumerate(self.qual_model_plugin.transitions):
            input_names = [
                qual_species.qualitative_species
                for qual_species in transition.getListOfInputs()
            ]
            output_names = [
                qual_species.qualitative_species
                for qual_species in transition.getListOfOutputs()
            ]

            # Cannot be parsed by sympy as the formula is conditional
            rate_law = formulaToL3String(
                transition.getListOfFunctionTerms()[0].getMath()
            )

            inputs = _lookup_concepts_filtered(input_names)
            outputs = _lookup_concepts_filtered(output_names)

            # Add a case for modifiers
            if len(inputs) == 1 and len(outputs) == 1:
                templates.append(
                    NaturalConversion(
                        subject=inputs[0],
                        outcome=outputs[0],
                        rate_law=None,
                    )
                )

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


def _extract_concept(species, units=None, model_id=None):
    species_id = species.getId()
    species_name = species.getName()
    display_name = species_name

    annotation_string = species.getAnnotationString()

    # namespace error when using etree with a qualitative species' annotation string
    # annotation_tree = etree.fromstring(annotation_string)

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


def get_model_annotations(sbml_model) -> Annotations:
    ann_xml = sbml_model.getAnnotationString()
    if not ann_xml:
        return None


def get_model_id(sbml_model):
    """Get the model ID from the SBML model annotation."""
    ann_xml = sbml_model.getAnnotationString()
    if not ann_xml:
        return None


apoptosis_file_new = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Apoptosis_stable.sbml?ref_type=heads"
)

coagulation_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Coagulation-pathway_stable.sbml?ref_type=heads"
)


stress_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/ER_Stress_stable.sbml?ref_type=heads"
)


def test_qual_own():
    xml_string = stress_file.text
    sbml_document = SBMLReader().readSBMLFromString(xml_string)
    sbml_document.setPackageRequired("qual", True)
    model = sbml_document.getModel()
    qual_model_plugin = model.getPlugin("qual")
    processor = SbmlQualProcessor(model, qual_model_plugin)


def test_old():
    model_id = "BIOMD0000000955"
    from mira.sources.biomodels import (
        get_sbml_model,
        template_model_from_sbml_string,
    )

    xml_string = get_sbml_model(model_id)
    model = template_model_from_sbml_string(xml_string)
