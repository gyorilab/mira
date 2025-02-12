__all__ = ["SBMLModel", "template_model_to_petrinet_sbml_file",
           "template_model_to_sbml"]

import json
import logging
from copy import deepcopy
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict
from libsbml import SBMLDocument

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

        sbml_document = SBMLDocument(model.template_model.sbml_level,
                                model.template_model.sbml_version)
        sbml_model = sbml_document.createModel()

        model_anns = model.template_model.annotations
        if model_anns:
            if model_anns.name:
                self.model_name = model_anns.name
            if model_anns.description and model_anns.description.examples:
                self.model_description = model_anns.description.examples[0]

        for model_key, model_param in model.parameters.items():
            if not isinstance(model_key,str):
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
        return name

    def to_xml_file(self, fname, name=None, description=None,
                    model_version=None, **kwargs):
        """Write the Petri net model to a JSON file

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
            Additional keyword arguments to pass to :func:`json.dump`.
        """
        indent = kwargs.pop('indent', 1)
        js = self.to_xml(name=name, description=description,
                         model_version=model_version)
        with open(fname, 'w') as fh:
            json.dump(js, fh, indent=indent, **kwargs)


def template_model_to_sbml(tm: TemplateModel):
    """Convert a template model to a PetriNet JSON dict.

    Parameters
    ----------
    tm :
        The template model to convert.

    Returns
    -------
    A JSON dict representing the PetriNet model.
    """
    model = Model(tm)
    return SBMLModel(Model(tm)).to_xml()


def template_model_to_petrinet_sbml_file(tm: TemplateModel, fname):
    """Convert a template model to a PetriNet JSON file.

    Parameters
    ----------
    tm :
        The template model to convert.
    fname : str
        The file name to write to.
    """
    SBMLModel(Model(tm)).to_xml_file(fname)

