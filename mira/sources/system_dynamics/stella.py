"""This module implements an API interface for retrieving Stella models by ISEE Systems
denoted by the .xmile, .itmx, or .stmx extension through  a locally downloaded file or URL. We
then convert the Stella model into a generic pysd model object that will be parsed and converted to an
equivalent MIRA template model.

Landing page for Stella: https://www.iseesystems.com/store/products/stella-online.aspx

Website containing sample Stella models: https://www.vensim.com/documentation/sample_models.html
"""

__all__ = ["template_model_from_stella_model_file", "template_model_from_stella_model_url"]

import tempfile
from pathlib import Path

import pysd
from pysd.translators.xmile.xmile_file import XmileFile
import requests

from mira.metamodel import TemplateModel
from mira.sources.system_dynamics.parse_pysd_model import (
    template_model_from_pysd_model,
)


def template_model_from_stella_model_file(fname) -> TemplateModel:
    """Return a template model from a local Stella model file

    Parameters
    ----------
    fname : str
        The path to the local Stella model file

    Returns
    -------
    :
        A MIRA template model
    """
    pysd_model = pysd.read_xmile(fname)
    stella_model_file = XmileFile(fname)
    return template_model_from_pysd_model(pysd_model)


def template_model_from_stella_model_url(url) -> TemplateModel:
    """Return a template model from a Stella model file provided by an url

    Parameters
    ----------
    url : str
        The url to the Stella model file

    Returns
    -------
    :
        A MIRA Template Model
    """

    file_extension = Path(url).suffix
    data = requests.get(url).content
    temp_file = tempfile.NamedTemporaryFile(
        mode="w+b", suffix=file_extension, delete=False
    )

    with temp_file as file:
        file.write(data)

    pysd_model = pysd.read_xmile(temp_file.name)
    stella_model_file = XmileFile(temp_file.name)

    return template_model_from_pysd_model(pysd_model)

