"""This module implements generation into SBML models."""


__all__ = [
    "SBMLModel",
    "template_model_to_sbml_file",
    "template_model_to_sbml_string",
]


from libsbml import (
    SBMLDocument,
    parseL3Formula,
    writeSBMLToString,
    writeSBMLToFile,
    RDFAnnotationParser,
    XMLNode,
    XMLToken,
    XMLTriple
)


from mira.metamodel import ReversibleFlux, TemplateModel
from mira.modeling import Model
from mira.sources.sbml.utils import *


class SBMLModel:
    """A class representing a SBML model."""

    def __init__(self, model: Model):
        """Instantiate a SBML model from a generic transition model.

        Parameters
        ----------
        model:
            The pre-compiled transition model
        """
        self.sbml_xml = ""

        # Default to level 3 version 1 for now
        self.sbml_level = 3
        self.sbml_version = 1
        self.sbml_document = SBMLDocument(self.sbml_level, self.sbml_version )
        sbml_model = self.sbml_document.createModel()

        # .parameters, .compartments, .species, .function_definitions, .rules,
        # .reactions, .unit_definitions, .annotations

        # set annotations so model_id can be propogated to add grounding

        # def _process_units():
        #     for _model_param in model.parameters.items():
        #         if model_param.concept.units:
        #             expression = model_param.concept.units.expression
        #             for free_symbol in expression:
        #                 str_free_symbol = str(free_symbol)
        #                 if str_free_symbol in self.units_map:
        #                     continue
        #                 else:
        #                     unit_def = sbml_model.createUnitDefinition()
        #                     if str_free_symbol == "day":
        #                         unit_def.setId("day")
        #                         day_unit = unit_def.createUnit()
        #                         day_unit.setKind(
        #                             UNIT_KIND_SECOND)  # Use second for "day" and set exponent to 86400 (number of seconds in a day)
        #                         day_unit.setExponent(1)
        #                         day_unit.setScale(0)
        #                         day_unit.setMultiplier(86400)


        rdf_parser = RDFAnnotationParser()
        sbml_compartment = sbml_model.createCompartment()
        sbml_compartment.setId("DefaultCompartment")
        sbml_compartment.setSize(1)

        for concept in model.template_model.get_concepts_map().values():
            sbml_species = sbml_model.createSpecies()

            if concept.identifiers:
                # Setting species annotations using XMLNode class from Libsbml, having trouble adding child nodes
                species_annotation_node = rdf_parser.createAnnotation()
                rdf_annotation_node = rdf_parser.createRDFAnnotation(self.sbml_level, self.sbml_version)
                rdf_description_node = XMLNode("rdf:Description")
                rdf_description_node.addAttr("rdf:about", "#COPASI9")
                rdf_annotation_node.addChild(rdf_description_node)
                species_annotation_node.addChild(rdf_annotation_node)
                sbml_species.setAnnotation(species_annotation_node)


            sbml_species.setId(concept.name)
            sbml_species.setName(concept.name)
            str_initial_expression = str(
                model.template_model.initials[concept.name].expression
            )
            try:
                initial_float = float(str_initial_expression)
                sbml_species.setInitialAmount(initial_float)
            except ValueError:
                # if the initial condition is an expression
                initial_assignment = sbml_model.createInitialAssignment()
                initial_assignment.setSymbol(sbml_species.getId())
                initial_assignment.setMath(
                    parseL3Formula(str_initial_expression)
                )
            # if concept.units.expression:
            #     # unit_expression = concept.units.expression
            #     # sbml_species_unit = sbml_model.createUnitDefinition()
            #     # # place-holder for unit id right now
            #     # sbml_species_unit.setId("species_unit")
            #     # self.units.add(concept.units.expression)
            #     pass
            sbml_species.setCompartment("DefaultCompartment")
            sbml_model.addSpecies(sbml_species)

        for model_key, model_param in model.parameters.items():
            if not isinstance(model_key, str):
                continue
            sbml_param = sbml_model.createParameter()
            sbml_param.setId(model_param.key)
            if model_param.display_name:
                sbml_param.setName(model_param.display_name)
            else:
                sbml_param.setName(model_param.key)

            # Boolean check returns false for parameter value of 0
            if hasattr(model_param, "value"):
                sbml_param.setValue(model_param.value)
            # if model_param.concept.units:
            #     # Doesn't work for now
            #     # Can look at free symbols
            #     # sbml_param.setUnits(str(model_param.concept.units.expression))
            #     # self.units.add(model_param.concept.units.expression)
            #     pass
            # Currently can't add model distributions as the distrib package isn't enabled
            # Tried to install a version of libsbml that has the distrib package enabled but couldn't do it
            # if model_param.distribution:
            #     pass

        for key, transition in model.transitions.items():
            sbml_reaction = sbml_model.createReaction()
            if not isinstance(transition.template, ReversibleFlux):
                sbml_reaction.setReversible(False)
            if transition.template.name:
                sbml_reaction.setId(transition.template.name)
            elif transition.template.display_name:
                sbml_reaction.setId(transition.template.display_name)

            for reactant in transition.consumed:
                sbml_reaction_reactant = sbml_reaction.createReactant()
                sbml_reaction_reactant.setSpecies(reactant.concept.name)

            for product in transition.produced:
                sbml_reaction_product = sbml_reaction.createProduct()
                sbml_reaction_product.setSpecies(product.concept.name)

            for modifier in transition.control:
                sbml_reaction_modifier = sbml_reaction.createModifier()
                sbml_reaction_modifier.setSpecies(modifier.concept.name)

            rate_law = parseL3Formula(str(transition.template.rate_law))

            kinetic_law = sbml_reaction.createKineticLaw()
            kinetic_law.setMath(rate_law)

        self.sbml_xml = writeSBMLToString(self.sbml_document)

    def to_xml(self):
        """Return a xml string of the SBML model

        Returns
        -------
        : string
            A xml string representing the SBML model.
        """
        return self.sbml_xml

    def to_xml_file(self, fname):
        """Write the SBML model to a xml file

        Parameters
        ----------
        fname : str
            The file name to write to.
        """
        writeSBMLToFile(self.sbml_document, fname)


def template_model_to_sbml_string(tm: TemplateModel):
    """Convert a template model to a SBML xml string.

    Parameters
    ----------
    tm :
        The template model to convert.

    Returns
    -------
    An xml string representing the SBML model.
    """
    return SBMLModel(Model(tm)).to_xml()


def template_model_to_sbml_file(tm: TemplateModel, fname):
    """Convert a template model to a SBML xml file.

    Parameters
    ----------
    tm :
        The template model to convert.
    fname : str
        The file name to write to.
    """
    SBMLModel(Model(tm)).to_xml_file(fname)
