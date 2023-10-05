__all__ = ['transition_to_templates', 'get_sympy']

import sympy
from typing import Optional
from mira.metamodel import *


def transition_to_templates(transition_rate, input_concepts, output_concepts,
                            controller_concepts, symbols, transition_id):
    """Return a list of templates from a transition"""
    rate_law = get_sympy(transition_rate, local_dict=symbols)

    if not controller_concepts:
        if not input_concepts:
            for output_concept in output_concepts:
                yield NaturalProduction(outcome=output_concept,
                                        rate_law=rate_law,
                                        name=transition_id)
        elif not output_concepts:
            for input_concept in input_concepts:
                yield NaturalDegradation(subject=input_concept,
                                         rate_law=rate_law,
                                         name=transition_id)
        else:
            for input_concept in input_concepts:
                for output_concept in output_concepts:
                    yield NaturalConversion(subject=input_concept,
                                            outcome=output_concept,
                                            rate_law=rate_law,
                                            name=transition_id)
    else:
        if not (len(input_concepts) == 1 and len(output_concepts) == 1):
            if len(input_concepts) == 1 and not output_concepts:
                if len(controller_concepts) > 1:
                    yield GroupedControlledDegradation(controllers=controller_concepts,
                                                       subject=input_concepts[0],
                                                       rate_law=rate_law,
                                                       name=transition_id)
                else:
                    yield ControlledDegradation(controller=controller_concepts[0],
                                                subject=input_concepts[0],
                                                rate_law=rate_law,
                                                name=transition_id)
            elif len(output_concepts) == 1 and not input_concepts:
                if len(controller_concepts) > 1:
                    yield GroupedControlledProduction(controllers=controller_concepts,
                                                      outcome=output_concepts[0],
                                                      rate_law=rate_law,
                                                      name=transition_id)
                else:
                    yield ControlledProduction(controller=controller_concepts[0],
                                               outcome=output_concepts[0],
                                               rate_law=rate_law,
                                               name=transition_id)
            else:
                return []

        elif len(controller_concepts) == 1:
            yield ControlledConversion(controller=controller_concepts[0],
                                       subject=input_concepts[0],
                                       outcome=output_concepts[0],
                                       rate_law=rate_law,
                                       name=transition_id)
        else:
            yield GroupedControlledConversion(controllers=controller_concepts,
                                              subject=input_concepts[0],
                                              outcome=output_concepts[0],
                                              rate_law=rate_law)


def get_sympy(expr_data, local_dict=None) -> Optional[sympy.Expr]:
    """Return a sympy expression from a dict with an expression or MathML

    Sympy string expressions are prioritized over MathML.

    Parameters
    ----------
    expr_data :
        A dict with an expression and/or MathML
    local_dict :
        A dict of local variables to use when parsing the expression

    Returns
    -------
    :
        A sympy expression or None if no expression was found
    """
    if expr_data is None:
        return None

    # Sympy
    if expr_data.get("expression"):
        expr = safe_parse_expr(expr_data["expression"], local_dict=local_dict)
    # MathML
    elif expr_data.get("expression_mathml"):
        expr = mathml_to_expression(expr_data["expression_mathml"])
    # No expression found
    else:
        expr = None
    return expr
