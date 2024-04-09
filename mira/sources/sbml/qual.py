import logging
from typing import List, Mapping

from mira.metamodel import *

import sympy
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

        # parameters and compartment attributes for sbml_model are empty, they don't exist for
        # the qual_model_plugin

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
            # 1 controller (negative or positive). Will never have a natural template

            # Since we always have at least one input and one output, not expecting any
            # degradation or production templates.
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

    annotation_string = None

    # annotation_string = species.getAnnotationString()

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


# models do not have an annotation string
def get_model_annotations(sbml_model):
    """Get the model annotations from the SBML model."""
    ann_xml = sbml_model.getAnnotationString()
    if not ann_xml:
        return None


# models do not have an annotation string
def get_model_id(sbml_model):
    """Get the model ID from the SBML model annotation."""
    ann_xml = sbml_model.getAnnotationString()
    if not ann_xml:
        return None
