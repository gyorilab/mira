__all__ = ["model_from_json_file", "model_to_json_file",
           "expression_to_mathml", "mathml_to_expression"]

import json
import sympy
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

        # Issue is that expression is usually of type SympyExprStr in test_model_api's case and this method expects that
        # expression.args[0] is of type symbol or a Sympy operation such as Mul, Add, Sub
        # However, expression.args[0] is of type string since we introduced the change to initials and then error
        # occurs when you call the atoms method on it
        expression = expression.args[0]

        # If expression.args[0] is a primitive data type, recast it as a Sympy Object, so we can run the for loop
        if isinstance(expression, str):
            if '.' in expression:
                expression = sympy.Float(expression)
            else:
                expression = sympy.Integer(expression)
        elif isinstance(expression, float):
            expression = sympy.Float(expression)
        elif isinstance(expression, int):
            expression = sympy.Integer(expression)

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
    from sbmlmath import SBMLMathMLParser
    template = """<?xml version="1.0" encoding="UTF-8"?>
    <math xmlns="http://www.w3.org/1998/Math/MathML">
    {xml_str}
    </math>"""
    xml_str = template.format(xml_str=xml_str)
    return SBMLMathMLParser().parse_str(xml_str)
