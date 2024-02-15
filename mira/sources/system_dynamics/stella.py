"""This module implements an API interface for retrieving Stella models by ISEE Systems
denoted by the .xmile, .xml, or .stmx extension through a locally downloaded file or URL. We
cannot process stella models with the .itmx extension. Additionally, the PySD library depends on
the parsimonious library which fails to parse a number of stella models with valid file
extensions due to incompatible symbols and characters in equations for variables. We implemented
preprocessing for stella models that fixes a number of these parsing
errors when using PySD to ingest these models; however, a number of models still fail to be
parsed by PySD's "read_xmile" method. We extract the contents of the model as a string,
perform expression preprocessing, and then convert the Stella model into a generic pysd model
object that will be converted to an equivalent MIRA template model.

Landing page for Stella: https://www.iseesystems.com/store/products/stella-online.aspx

Website containing sample Stella models: https://www.vensim.com/documentation/sample_models.html
"""

__all__ = [
    "template_model_from_stella_model_file",
    "template_model_from_stella_model_url",
    "template_model_stella_model_string",
]

import tempfile
import re

import pysd
from pysd.translators.xmile.xmile_file import XmileFile
from pysd.translators.xmile.xmile_element import (
    ControlElement,
    Aux,
    Stock,
    Flow,
)
from pysd.translators.structures.abstract_expressions import (
    ArithmeticStructure,
    ReferenceStructure,
    InlineLookupsStructure,
)
import requests

from mira.metamodel import TemplateModel
from mira.sources.system_dynamics.pysd import (
    template_model_from_pysd_model,
)

PLACE_HOLDER_EQN = "<eqn>0</eqn>"


def template_model_from_stella_model_file(fname) -> TemplateModel:
    """Return a template model from a local Stella model file

    Parameters
    ----------
    fname : str or pathlib.Path
        The path to the local Stella model file

    Returns
    -------
    :
        A MIRA template model
    """
    with open(fname) as f:
        xml_str = f.read()

    return template_model_stella_model_string(xml_str)


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

    xml_str = requests.get(url).text
    return template_model_stella_model_string(xml_str)


def template_model_stella_model_string(xml_str) -> TemplateModel:
    """Returns a semantically equivalent template model to the stella model represented by the
    xml string

    Parameters
    ----------
    xml_str : The contents of the Stella model

    Returns
    -------
    :
        A MIRA template model
    """
    xml_str = process_string(xml_str)
    temp_file = tempfile.NamedTemporaryFile(
        mode="w+", suffix=".stmx", delete=False
    )

    with temp_file as file:
        file.write(xml_str)

    pysd_model = pysd.read_xmile(temp_file.name)
    stella_model_file = XmileFile(temp_file.name)
    stella_model_file.parse()
    expression_map = extract_stella_variable_expressions(stella_model_file)

    return template_model_from_pysd_model(pysd_model, expression_map)


def extract_stella_variable_expressions(stella_model_file):
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
    operand_operator_per_level_var_map = {}

    for component in stella_model_file.sections[0].components:
        if isinstance(component, ControlElement):
            continue
        # test to see if flow first as flow is a subclass or Aux
        elif isinstance(component, Flow):
            # TODO: test for call structure object
            # if primitive represents flow rate expression
            if not hasattr(component.components[0][1], "arguments"):
                expression_map[component.name] = str(component.components[0][1])
                continue
            operands = component.components[0][1].arguments
            # If the flow doesn't use operands (e.g. +,-) but actual functions (e.g. max,pulse)
            # assign the flow as None
            if not hasattr(component.components[0][1], "operators"):
                expression_map[component.name] = "xxplaceholderxx"
                continue
            operators = component.components[0][1].operators
            operand_operator_per_level_var_map[component.name] = {}
            extract_variables(
                operands,
                operators,
                component.name,
                operand_operator_per_level_var_map,
            )
        elif isinstance(component, Aux):
            # TODO: test for call structure object
            # TODO: Add more comprehensive coverage for different expression structures for Aux
            #  and Flows
            if not isinstance(component.components[0][1], ArithmeticStructure):
                if isinstance(
                    component.components[0][1], InlineLookupsStructure
                ):
                    # current place holder value
                    expression_map[component.name] = "-1"
                    continue
                expression_map[component.name] = parse_aux_structure(component)
                continue
            operands = component.components[0][1].arguments
            operators = component.components[0][1].operators
            operand_operator_per_level_var_map[component.name] = {}
            extract_variables(
                operands,
                operators,
                component.name,
                operand_operator_per_level_var_map,
            )

        elif isinstance(component, Stock):
            try:
                operand_operator_per_level_var_map[component.name] = {}
                operands = component.components[0][1].flow.arguments
                operators = component.components[0][1].flow.operators
                extract_variables(
                    operands,
                    operators,
                    component.name,
                    operand_operator_per_level_var_map,
                )
            # If the stock only has a reference and no operators in its expression
            except AttributeError:
                stock_flow = component.components[0][1].flow
                if hasattr(stock_flow, "reference"):
                    expression_map[component.name] = replace_backslash(
                        stock_flow.reference
                    )
                else:
                    expression_map[component.name] = stock_flow

                operand_operator_per_level_var_map[component.name] = {}
                operand_operator_per_level_var_map[component.name][0] = {}
                operand_operator_per_level_var_map[component.name][0][
                    "operands"
                ] = (
                    [replace_backslash(stock_flow.reference)]
                    if hasattr(stock_flow, "reference")
                    else [stock_flow]
                )

    # construct the expression for each variable once its operators and operands are mapped
    for var_name, expr_level_dict in operand_operator_per_level_var_map.items():
        expression_map[var_name] = create_expression(expr_level_dict)
    return expression_map


def create_expression(expr_level_dict):
    """When a variable's operators and operands are mapped, construct the string expression

    Parameters
    ----------
    expr_level_dict : dict[int,Any]
        The mapping of level to operands and operators present in a level of an expression
    Returns
    -------
    : str
        The string expression
    """
    str_expression = ""
    for level, ops in reversed(expr_level_dict.items()):
        operands = ops["operands"]
        operators = ops["operators"] if ops.get("operators") else []
        if not operators:
            level_expr = operands[0]
            str_expression += str(level_expr)
            continue
        elif len(operands) > len(operators):
            level_expr = "("
            for idx, operand in enumerate(operands):
                try:
                    if operators[idx] != "negative":
                        if level == len(expr_level_dict) - 1:
                            level_expr += operand + operators[idx]
                        else:
                            level_expr += operators[idx] + operand
                    else:
                        level_expr += "-" + operand
                except IndexError:
                    level_expr += operands[len(operands) - 1]
            str_expression += level_expr + ")"
        elif len(operands) == len(operators):
            level_expr = ""
            for idx, operand in enumerate(operands):
                if operators[idx] != "negative":
                    if level == len(expr_level_dict) - 1:
                        level_expr = operand + operators[idx]
                    else:
                        level_expr = operators[idx] + operand
                else:
                    level_expr += "-" + operand
                str_expression += level_expr
    return str_expression


def extract_variables(
    operands, operators, name, operand_operator_per_level_var_map
):
    """Helper method to construct an expression for each variable in a Stella model

    Parameters
    ----------
    operands : list[ReferenceStructure,ArithmeticStructure]
        List of ReferenceStructure objects representing operands in an expression for a variable
    operators : list[str]
        List of operators in an expression for a variable
    name : str
        Name of the variable
    operand_operator_per_level_var_map : dict[str,Any]
        Mapping of variable name to operators and operands associated with the level they are
        encountered

    """
    operand_operator_per_level_var_map[name][0] = {}
    operand_operator_per_level_var_map[name][0]["operators"] = []
    operand_operator_per_level_var_map[name][0]["operands"] = []
    operand_operator_per_level_var_map[name][0]["operators"].extend(operators)
    for idx, operand in enumerate(operands):
        parse_structures(operand, 0, name, operand_operator_per_level_var_map)


def parse_structures(operand, idx, name, operand_operator_per_level_var_map):
    """Recursive helper method that retrieves each operand associated with a ReferenceStructure
    object and operators associated with an ArithmeticStructure object. ArithmeticStructures can
    contain ArithmeticStructure or ReferenceStructure Objects.

    Parameters
    ----------
    operand : ReferenceStructure or ArithmeticStructure
        The operand in an expression
    idx : int
        The level at which the operand is encountered in an expression (e.g. 5+(7-3). The
        operands 7 and 3 are considered as level 1 and 5 is considered as level 5).
    name : str
        The name of the variable
    operand_operator_per_level_var_map : dict[str,Any]
        Mapping of variable name to operators and operands associated with the level they are
        encountered
    """
    if operand_operator_per_level_var_map[name].get(idx) is None:
        operand_operator_per_level_var_map[name][idx] = {}
        operand_operator_per_level_var_map[name][idx]["operators"] = []
        operand_operator_per_level_var_map[name][idx]["operands"] = []

    # base case
    if isinstance(operand, ReferenceStructure):
        operand_operator_per_level_var_map[name][idx]["operands"].append(
            replace_backslash(operand.reference)
        )
    elif isinstance(operand, ArithmeticStructure):
        for struct in operand.arguments:
            parse_structures(
                struct, idx + 1, name, operand_operator_per_level_var_map
            )
        operand_operator_per_level_var_map[name][idx + 1]["operators"].extend(
            operand.operators
        )

    # case where operand is just a primitive
    else:
        operand_operator_per_level_var_map[name][idx]["operands"].append(
            str(operand)
        )


def parse_aux_structure(structure):
    """If an Aux object's component method is not a reference structure, deconstruct the Aux object
    to retrieve the primitive value that the auxiliary represents

    Parameters
    ----------
    structure : Aux
        The Aux object
    Returns
    -------

    """
    val = structure.components[0][1]
    while (
        not isinstance(val, float)
        and not isinstance(val, str)
        and not isinstance(val, int)
    ):
        if hasattr(val, "argument"):
            val = val.argument
        if isinstance(val, ReferenceStructure):
            val = replace_backslash(val.reference)
    return str(val)


def process_string(xml_str):
    """Helper method that removes incompatible characters from expressions for
    variables such that the stella model file can be read by PySD's "read_xmile" method

    Parameters
    ----------
    xml_str : str
        The xml string representing the contents of the model

    Returns
    -------
    : str
        The xml string represent the contents of the model after expressions have been
        preprocessed
    """
    xml_str = xml_str.replace("\n", "")

    eqn_tags = re.findall(r"<eqn>.*?</eqn>", xml_str, re.DOTALL)
    for tag in eqn_tags:
        if all(word in tag.lower() for word in ["if", "then", "else"]):
            xml_str = xml_str.replace(tag, PLACE_HOLDER_EQN)
        if all(word in tag.lower() for word in ["int", "mod", "(", ")"]):
            xml_str = xml_str.replace(tag, PLACE_HOLDER_EQN)
        if all(word in tag.lower() for word in ["ln", "(", ")"]):
            xml_str = xml_str.replace(tag, PLACE_HOLDER_EQN)
        if "sum" in tag.lower():
            xml_str = xml_str.replace(tag, PLACE_HOLDER_EQN)
        if "//" in tag.lower():
            xml_str = xml_str.replace(tag, PLACE_HOLDER_EQN)
        if "," in tag.lower():
            xml_str = xml_str.replace(tag, PLACE_HOLDER_EQN)
        if "init" in tag.lower():
            xml_str = xml_str.replace(tag, PLACE_HOLDER_EQN)
        if "nan" in tag.lower():
            xml_str = xml_str.replace(tag, PLACE_HOLDER_EQN)
        if "pi" in tag.lower():
            xml_str = xml_str.replace(tag, PLACE_HOLDER_EQN)

    # Comment preprocessing
    eqn_bracket_pattern = r"(<eqn>.*?)\{[^}]*\}(.*?</eqn>)"
    eqn_bracket_sub = r"\1" + r"\2"
    xml_str = re.sub(eqn_bracket_pattern, eqn_bracket_sub, xml_str)

    return xml_str


def replace_backslash(name):
    """Helper method to remove backslashes from variable names

    Parameters
    ----------
    name : str
        The name of the variable

    Returns
    -------
    : str
        The name of the variable with backslashes removed
    """
    return name.replace("\\\\", "")
