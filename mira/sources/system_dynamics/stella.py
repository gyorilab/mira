"""This module implements an API interface for retrieving Stella models by ISEE Systems
denoted by the .xmile, .xml, or .stmx extension through a locally downloaded file or URL. We
then convert the Stella model into a generic pysd model object that will be parsed and converted to
an equivalent MIRA template model. We preprocess the stella model file to extract variable
expressions.

Landing page for Stella: https://www.iseesystems.com/store/products/stella-online.aspx

Website containing sample Stella models: https://www.vensim.com/documentation/sample_models.html
"""

__all__ = [
    "template_model_from_stella_model_file",
    "template_model_from_stella_model_url",
]

import tempfile
from pathlib import Path

import pysd
from pysd.translators.xmile.xmile_file import XmileFile
from pysd.translators.xmile.xmile_element import (
    ControlElement,
    Aux,
    Stock,
    Flow,
)
import requests

from mira.metamodel import TemplateModel
from mira.sources.system_dynamics.parse_pysd_model import (
    template_model_from_pysd_model,
)


def template_model_from_stella_model_file(fname) -> TemplateModel:
    """Return a template model from a local Stella model file

    Parameters
    ----------
    fname : Union[str,PosixPath]
        The path to the local Stella model file

    Returns
    -------
    :
        A MIRA template model
    """
    pysd_model = pysd.read_xmile(fname)
    stella_model_file = XmileFile(fname)
    stella_model_file.parse()
    expression_map = extract_stella_variable_info(stella_model_file)
    return template_model_from_pysd_model(pysd_model, expression_map)


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
    stella_model_file.parse()
    expression_map = extract_stella_variable_info(stella_model_file)

    return template_model_from_pysd_model(pysd_model, expression_map)


def extract_stella_variable_info(stella_model_file):
    """Method that extracts expressions for each variable in a Stella model

    Parameters
    ----------
    stella_model_file : XmileFile
        The XmileFile object

    Returns
    -------
    : dict[str,str]
        Mapping of variable name to string variable expression
    """
    expression_map = {}
    for component in stella_model_file.sections[0].components:
        if isinstance(component, ControlElement):
            continue
        elif isinstance(component, Flow):
            operands = component.components[0][1].arguments
            operators = component.components[0][1].operators
            expression_map[component.name] = construct_expression(
                operands, operators
            )
        elif isinstance(component, Aux):
            expression_map[component.name] = str(component.components[0][1])
        elif isinstance(component, Stock):
            try:
                operands = component.components[0][1].flow.arguments
                operators = component.components[0][1].flow.operators
                expression_map[component.name] = construct_expression(
                    operands, operators
                )
            except AttributeError:
                expression_map[component.name] = component.components[0][
                    1
                ].flow.reference
    return expression_map


def construct_expression(operands, operators):
    """Helper method to construct an expression for each variable in a Stella model

    Parameters
    ----------
    operands : list[ReferenceStructure]
        List of ReferenceStructure objects representing operands in an expression for a variable
    operators : list[str]
        List of operators in an expression for a variable

    Returns
    -------
    : str
        A string expression
    """
    str_expression = ""
    for idx, operand in enumerate(operands):
        try:
            if operators[idx] != "negative":
                str_expression += operand.reference + operators[idx]
            else:
                str_expression += "-" + operand.reference
        except IndexError:
            if len(operands) > len(operators):
                return str_expression + operands[len(operands) - 1].reference
    return str_expression
