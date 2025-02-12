__all__ = ["SBMLModel", "template_model_to_petrinet_sbml_file",
           "template_model_to_sbml"]

import json
import logging
from copy import deepcopy
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict
from libsbml import SBMLDocument, parseL3Formula, writeSBMLToString
import xml.etree.ElementTree as ET

from mira.metamodel import expression_to_mathml, TemplateModel, SympyExprStr
from mira.sources.amr import sanity_check_amr
from mira.sources.sbml import sbml_model_from_file
from mira.modeling import Model
from mira.sources.biomodels import get_template_model


class SBMLModel:

    def __init__(self, model: Model):

        self.properties = {}
        self.initials = []
        self.rates = []
        self.states = []
        self.transitions = []
        self.parameters = []
        self.metadata = {}
        self.time = None
        self.observables = []
        self.model_name = 'Model'
        self.model_description = 'Description'
        self.sbml_xml = ""

        sbml_level = model.template_model.sbml_level
        sbml_version = model.template_model.sbml_version
        sbml_document = SBMLDocument(sbml_level, sbml_version)
        sbml_model = sbml_document.createModel()

        # .parameters, .compartments, .species, .function_definitions, .rules, .reactions
        model_anns = model.template_model.annotations
        if model_anns:
            if model_anns.name:
                self.model_name = model_anns.name
            if model_anns.description and model_anns.description.examples:
                self.model_description = model_anns.description.examples[0]

        for model_key, model_param in model.parameters.items():
            if not isinstance(model_key, str):
                continue
            sbml_param = sbml_model.createParameter()
            sbml_param.setId(model_param.key)
            if model_param.display_name:
                sbml_param.setName(model_param.display_name)
            else:
                sbml_param.setName(model_param.key)
            if model_param.value:
                sbml_param.setValue(model_param.value)
            if model_param.concept.units:
                sbml_param.setUnits(str(model_param.concept.units.expression))
            # Currently can't add model distributions as the distrib package isn't enabled
            # Tried to install a version of libsbml that has the distrib package enabled but couldn't do it
            if model_param.distribution:
                pass

        for key, transition in model.transitions.items():
            sbml_reaction = sbml_model.createReaction()

            if transition.template.name:
                sbml_reaction.setId(transition.template.name)
            elif transition.template.display_name:
                sbml_reaction.setId(transition.template.display_name)

            for reactant in transition.consumed:
                sbml_reaction_reactant = sbml_reaction.createReactant()
                sbml_reaction_reactant.setId(reactant.concept.name)
                sbml_reaction_reactant.setSpecies(reactant.concept.name)

            for product in transition.produced:
                sbml_reaction_product = sbml_reaction.createProduct()
                sbml_reaction_product.setId(product.concept.name)
                sbml_reaction_product.setSpecies(product.concept.name)

            for modifier in transition.control:
                sbml_reaction_modifier = sbml_reaction.createModifier()
                sbml_reaction_modifier.setId(modifier.concept.name)
                sbml_reaction_modifier.setSpecies(modifier.concept.name)

            rate_law = parseL3Formula(str(transition.template.rate_law))

            kinetic_law = sbml_reaction.createKineticLaw()
            kinetic_law.setMath(rate_law)

        self.sbml_xml = writeSBMLToString(sbml_document)

    def to_xml(
        self,
        name: str = None,
        description: str = None,
        model_version: str = None
    ):
        """Return a JSON dict structure of the Petri net model.

        Parameters
        ----------
        name :
            The name of the model. Defaults to the name of the original
            template model that produced the input Model instance or, if not
            available, 'Model'.
        description :
            A description of the model. Defaults to the description of the
            original template model that produced the input Model instance or,
            if not available, the name of the model.
        model_version :
            The version of the model. Defaults to '0.1'.

        Returns
        -------
        : JSON
            A JSON dict representing the Petri net model.
        """
        return self.sbml_xml

    def to_xml_file(self, fname, name=None, description=None,
                    model_version=None, **kwargs):
        """Write the SBML model to a xml file

        Parameters
        ----------
        fname : str
            The file name to write to.
        name : str, optional
            The name of the model.
        description : str, optional
            A description of the model.
        model_version : str, optional
            The version of the model.
        kwargs :
            Additional keyword arguments to pass to :func:`tree.write`.
        """
        root = self.to_xml(name=name, description=description,
                         model_version=model_version)
        xml_tree = ET.ElementTree(root)
        with open(fname, 'w') as fh:
            xml_tree.write(fh, xml_declaration=True, **kwargs)


def template_model_to_sbml(tm: TemplateModel):
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


def template_model_to_petrinet_sbml_file(tm: TemplateModel, fname):
    """Convert a template model to a SBML xml file.

    Parameters
    ----------
    tm :
        The template model to convert.
    fname : str
        The file name to write to.
    """
    SBMLModel(Model(tm)).to_xml_file(fname)
