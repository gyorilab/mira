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
from libsbml import formulaToL3String, parseL3Formula
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

        # all_parameters = {
        #     parameter.id: {
        #         "value": parameter.value,
        #         "description": parameter.name,
        #         "units": self.get_object_units(parameter),
        #     }
        #     for parameter in self.sbml_model.parameters
        # }
        #
        # parameter_symbols = {
        #     parameter.id: sympy.Symbol(parameter.id)
        #     for parameter in self.sbml_model.parameters
        # }
        # compartment_symbols = {
        #     compartment.id: sympy.Symbol(compartment.id)
        #     for compartment in self.sbml_model.compartments
        # }

        # instead of a simple logic formula, there is a flag called qual:sign = positive
        # then there exists a formula, positive controller means it controls the prooduction
        # of something
        # if there's a qual:sign = negative,
        # qual negative means there's a controller which controls degradation
        # if both positive and negative exists, it is production process, with a list of
        # controllers from both the negative and positive side.

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
            # Inputs will always be 0 or 1
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

            # transitions always have at least one input and one output
            # Since we always have at least one input, there will always be at least
            # 1 controller (negative or positive). How does this translate to templates?
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
                    # Since inputs are only positive or negative, won't have overlapping concepts
                    # when adding the two lists together
                    templates.append(
                        GroupedControlledProduction(
                            controllers=positive_controller_concepts
                            + negative_controller_concepts,
                            outcome=output_concepts[0],
                            name=transition_id,
                            display_name=transition_name,
                        )
                    )

        # initial level for each species is intMax, due to libsbml processing, not actually
        # stored in the model
        # use current level of species for now
        initials = {}
        for qual_species in self.qual_model_plugin.qualitative_species:
            initials[qual_species.name] = Initial(
                concept=concepts[qual_species.id],
                expression=SympyExprStr(qual_species.level),
            )

        template_model = TemplateModel(
            templates=templates, initials=initials, annotations=model_annots
        )
        return template_model

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


def get_model_annotations(sbml_model):
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

etc_stable_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/ETC_stable.sbml?ref_type=heads"
)

e_protein_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/E_protein_stable.sbml?ref_type=heads"
)

hmox1_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/HMOX1_Pathway_stable.sbml?ref_type=heads"
)

ifn_lambda_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/IFN-lambda_stable.sbml?ref_type=heads"
)

interferon_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Interferon1_stable.sbml?ref_type=heads"
)

jnk_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/JNK_pathway_stable.sbml?ref_type=heads"
)
kyu_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Kynurenine_pathway_stable.sbml?ref_type=heads"
)
nlrp3_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/NLRP3_Activation_stable.sbml?ref_type=heads"
)
nsp_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Nsp14_stable.sbml?ref_type=heads"
)
nsp4_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Nsp4_Nsp6_stable.sbml?ref_type=heads"
)
nsp9_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Nsp9_protein_stable.sbml?ref_type=heads"
)
orf10_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Orf10_Cul2_pathway_stable.sbml?ref_type=heads"
)
orf3a_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Orf3a_stable.sbml?ref_type=heads"
)
pamp_signal_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/PAMP_signaling_stable.sbml?ref_type=heads"
)
pyrimidine_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Pyrimidine_deprivation_stable.sbml?ref_type=heads"
)
rtc_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/RTC-and-transcription_stable.sbml?ref_type=heads"
)
renin_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Renin_angiotensin_stable.sbml?ref_type=heads"
)
tgfb_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/TGFB_pathway_stable.sbml?ref_type=heads"
)
virus_file = requests.get(
    "https://git-r3lab.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml/Virus_replication_cycle_stable.sbml?ref_type=heads"
)
file_list = [
    stress_file,
    # apoptosis_file_new,
    # coagulation_file,
    # etc_stable_file,
    # e_protein_file,
    # hmox1_file,
    # ifn_lambda_file,
    # jnk_file,
    # kyu_file,
    # nlrp3_file,
    # nsp_file,
    # nsp4_file,
    # nsp9_file,
    # orf10_file,
    # orf3a_file,
    # pamp_signal_file,
    # pyrimidine_file,
    # rtc_file,
    # renin_file,
    # tgfb_file,
    # virus_file,
]


def test_qual():
    for file in file_list:
        xml_string = file.text
        sbml_document = SBMLReader().readSBMLFromString(xml_string)
        sbml_document.setPackageRequired("qual", True)
        model = sbml_document.getModel()
        qual_model_plugin = model.getPlugin("qual")
        processor = SbmlQualProcessor(model, qual_model_plugin)
        tm = processor.extract_model()


def test_old():
    model_id = "BIOMD0000000955"
    from mira.sources.biomodels import (
        get_sbml_model,
        template_model_from_sbml_string,
    )

    xml_string = get_sbml_model(model_id)
    model = template_model_from_sbml_string(xml_string)
