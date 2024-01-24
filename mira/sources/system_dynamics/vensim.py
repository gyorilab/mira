"""This module implements parsing Vensim models by Ventana Systems denoted by the .mdl file
and turning them into MIRA template models.

The documentation for vensim models is defined here:
https://www.vensim.com/documentation/sample_models.html

SIR mdl file example here: https://www.vensim.com/documentation/sample_models.html
"""

__all__ = ["template_model_from_mdl_file", "template_model_from_mdl_url"]

import tempfile

import pysd
from pysd.translators.vensim.vensim_file import VensimFile
import requests

from mira.metamodel import TemplateModel
from mira.sources.system_dynamics.parse_pysd_model import (
    template_model_from_pysd_model,
)


def template_model_from_mdl_file(fname) -> TemplateModel:
    """Return a template model from a local Vensim file

    Parameters
    ----------
    fname : str
        The path to the local Vensim file

    Returns
    -------
    :
        A MIRA template model
    """
    pysd_model = pysd.read_vensim(fname)
    vensim_file = VensimFile(fname)
    return template_model_from_pysd_model(pysd_model, vensim_file.model_text)


def template_model_from_mdl_url(url) -> TemplateModel:
    """Return a template model from a Vensim file provided by an url

    Parameters
    ----------
    url : str
        The url to the mdl file

    Returns
    -------
    :
        A MIRA Template Model
    """
    data = requests.get(url).content
    temp_file = tempfile.NamedTemporaryFile(
        mode="w+b", suffix=".mdl", delete=False
    )

    with temp_file as file:
        file.write(data)

    pysd_model = pysd.read_vensim(temp_file.name)
    vensim_file = VensimFile(temp_file.name)

    return template_model_from_pysd_model(pysd_model, vensim_file.model_text)


if __name__ == "__main__":
    template_model_from_mdl_url("https://raw.githubusercontent.com/SDXorg/test-models/master/samples/SIR/SIR.mdl")