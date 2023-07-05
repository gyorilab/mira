__all__ = ["model_from_json_file", "model_to_json_file",
           "expression_to_mathml", "mathml_to_expression"]

import json
import sympy
from sbmlmath import SBMLMathMLParser
from .template_model import TemplateModel, SympyExprStr


def model_from_json_file(fname) -> TemplateModel:
    """Return a TemplateModel from a JSON file.

    Parameters
    ----------
    fname : str or Path
        A file path.

    Returns
    -------
    :
        A TemplateModel deserialized from the JSON file.
    """
    with open(fname, 'r') as fh:
        return TemplateModel.from_json(json.load(fh))


def model_to_json_file(model: TemplateModel, fname):
    """Dump a TemplateModel into a JSON file.

    Parameters
    ----------
    model : TemplateModel
        A template model to dump to a JSON file.
    fname : str or Path
        A file path to dump the model into.
    """
    with open(fname, 'w') as fh:
        json.dump(json.loads(model.json()), fh, indent=1)


def expression_to_mathml(expression: sympy.Expr, *args, **kwargs) -> str:
    """Convert a sympy expression to MathML string.

    Here we pay attention to not style underscores and numeric suffixes
    in special ways.
    """
    if isinstance(expression, SympyExprStr):
        expression = expression.args[0]
    mappings = {}
    for sym in expression.atoms(sympy.Symbol):
        name = '|' + str(sym).replace('_', 'QQQ') + '|'
        mappings[str(sym)] = name
        expression = expression.subs(sym, sympy.Symbol(name))
    mml = sympy.mathml(expression, *args, **kwargs)
    for old_symbol, new_symbol in mappings.items():
        mml = mml.replace(new_symbol, old_symbol)
    return mml


def mathml_to_expression(xml_str: str) -> sympy.Expr:
    """Convert a MathML string to a sympy expression."""
    template = """<?xml version="1.0" encoding="UTF-8"?>
    <math xmlns="http://www.w3.org/1998/Math/MathML">
    {xml_str}"""
    xml_str = template.format(xml_str=xml_str)
    return SBMLMathMLParser().parse_str(xml_str)
