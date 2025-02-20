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
    CVTerm,
    BIOLOGICAL_QUALIFIER,
    MODEL_QUALIFIER,
    BQB_IS,
    BQB_HAS_PROPERTY,
    BQB_HAS_TAXON,
    BQM_IS,
    BQM_IS_DESCRIBED_BY
)


from mira.modeling import Model
from mira.sources.sbml.utils import *

URI_PARSING_PRIORITY_LIST = ["miriam", "bioregistry", "default"]

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
        self.sbml_document = SBMLDocument(self.sbml_level, self.sbml_version)
        sbml_model = self.sbml_document.createModel()
        tm_model_ann = model.template_model.annotations

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

        # set model annotations
        rdf_parser = RDFAnnotationParser()
        model_annotation_node = rdf_parser.createAnnotation()
        model_rdf_node = rdf_parser.createRDFAnnotation(self.sbml_level, self.sbml_version)
        sbml_model.setName(tm_model_ann.name)
        # place-holder value for model meta id
        sbml_model.setMetaId("model_metaid")

        # process model annotations
        for disease in tm_model_ann.diseases:
            disease_term = create_biological_cv_term(disease, BQB_IS)
            if disease_term:
                sbml_model.addCVTerm(disease_term)

        for publication in tm_model_ann.references:
            publication_term = create_model_cv_term(publication, BQM_IS_DESCRIBED_BY)
            if publication_term:
                sbml_model.addCVTerm(publication_term)

        for taxa in tm_model_ann.hosts + tm_model_ann.pathogens:
            taxa_term = create_biological_cv_term(taxa, BQB_HAS_TAXON)
            if taxa_term:
                sbml_model.addCVTerm(taxa_term)

        for model_type in tm_model_ann.model_types:
            model_type_term = create_biological_cv_term(model_type, BQB_HAS_PROPERTY)
            if model_type_term:
                sbml_model.addCVTerm(model_type_term)

        model_cvterms_node = RDFAnnotationParser.createCVTerms(sbml_model)
        if model_cvterms_node:
            model_rdf_node.addChild(model_cvterms_node)
        model_annotation_node.addChild(model_rdf_node)
        sbml_model.setAnnotation(model_annotation_node)

        compartment = sbml_model.createCompartment()
        compartment.setId("DefaultCompartment")
        compartment.setSize(1)

        for concept in model.template_model.get_concepts_name_map().values():
            species = sbml_model.createSpecies()
            species.setId(concept.name)

            # place-holder value for species meta id
            species.setMetaId(concept.name)
            species.setName(concept.name)
            if concept.identifiers:
                species_annotation_node = rdf_parser.createAnnotation()
                species_rdf_node = rdf_parser.createRDFAnnotation(
                    self.sbml_level, self.sbml_version
                )

                for prefix, identifier in concept.identifiers.items():
                    if prefix == "biomodels.species":
                        continue
                    else:
                        curie = f"{prefix}:{identifier}"
                        identifier_term = create_biological_cv_term(curie, BQB_IS)
                        if identifier_term:
                            species.addCVTerm(identifier_term)

                for curie in concept.context.values():
                    context_term = create_biological_cv_term(curie, BQB_HAS_PROPERTY)
                    if context_term:
                        species.addCVTerm(context_term)

                species_cvterms_node = RDFAnnotationParser.createCVTerms(species)
                if species_cvterms_node:
                    species_rdf_node.addChild(species_cvterms_node)
                species_annotation_node.addChild(species_rdf_node)
                species.setAnnotation(species_annotation_node)

            str_initial_expression = str(
                model.template_model.initials[concept.name].expression
            )
            try:
                initial_float = float(str_initial_expression)
                species.setInitialAmount(initial_float)
            except ValueError:
                # if the initial condition is an expression
                initial_assignment = sbml_model.createInitialAssignment()
                initial_assignment.setSymbol(species.getId())
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
            species.setCompartment("DefaultCompartment")
            sbml_model.addSpecies(species)

        for model_key, model_param in model.parameters.items():
            if not isinstance(model_key, str):
                continue
            parameter = sbml_model.createParameter()
            parameter.setId(model_param.key)
            if model_param.display_name:
                parameter.setName(model_param.display_name)
            else:
                parameter.setName(model_param.key)

            # Boolean check returns false for parameter value of 0
            if hasattr(model_param, "value"):
                parameter.setValue(model_param.value)
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
            reaction = sbml_model.createReaction()
            if not isinstance(transition.template, ReversibleFlux):
                reaction.setReversible(False)
            if transition.template.name:
                reaction.setId(transition.template.name)
            elif transition.template.display_name:
                reaction.setId(transition.template.display_name)

            for reactant in transition.consumed:
                sbml_reaction_reactant = reaction.createReactant()
                sbml_reaction_reactant.setSpecies(reactant.concept.name)

            for product in transition.produced:
                sbml_reaction_product = reaction.createProduct()
                sbml_reaction_product.setSpecies(product.concept.name)

            for modifier in transition.control:
                sbml_reaction_modifier = reaction.createModifier()
                sbml_reaction_modifier.setSpecies(modifier.concept.name)

            rate_law = parseL3Formula(str(transition.template.rate_law))

            kinetic_law = reaction.createKineticLaw()
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
