__all__ = ["transition_to_templates", "get_sympy", "parameter_to_mira"]

import sympy
from typing import Optional
from mira.metamodel import *


def transition_to_templates(
    input_concepts,
    output_concepts,
    controller_concepts,
    transition_rate,
    transition_id,
    transition_name=None,
):
    """
    Return a list of templates from a transition.

    Parameters
    ----------
    input_concepts : list[Concept]
        A list of Concepts serving as input to a transition.
    output_concepts : list[Concept]
        A list of Concepts serving as output to a transition.
    controller_concepts : list[Concept]
        A list of Concepts serving as controllers towards a transition.
    transition_rate : sympy.Expr
        The rate law associated with the transition.
    transition_id : str
        The id of the transition.
    transition_name : str
        The name of the transition.

    Returns
    -------
    : list[Template]
        A list containing Templates.
    """
    if not controller_concepts:
        if not input_concepts:
            for output_concept in output_concepts:
                yield NaturalProduction(
                    outcome=output_concept,
                    rate_law=transition_rate,
                    name=transition_id,
                    display_name=transition_name,
                )
        elif not output_concepts:
            for input_concept in input_concepts:
                yield NaturalDegradation(
                    subject=input_concept,
                    rate_law=transition_rate,
                    name=transition_id,
                    display_name=transition_name,
                )
        else:
            for input_concept in input_concepts:
                for output_concept in output_concepts:
                    yield NaturalConversion(
                        subject=input_concept,
                        outcome=output_concept,
                        rate_law=transition_rate,
                        name=transition_id,
                        display_name=transition_name,
                    )
    else:
        if not (len(input_concepts) == 1 and len(output_concepts) == 1):
            if len(input_concepts) == 1 and not output_concepts:
                if len(controller_concepts) > 1:
                    yield GroupedControlledDegradation(
                        controllers=controller_concepts,
                        subject=input_concepts[0],
                        rate_law=transition_rate,
                        name=transition_id,
                        display_name=transition_name,
                    )
                else:
                    yield ControlledDegradation(
                        controller=controller_concepts[0],
                        subject=input_concepts[0],
                        rate_law=transition_rate,
                        name=transition_id,
                        display_name=transition_name,
                    )
            elif len(output_concepts) == 1 and not input_concepts:
                if len(controller_concepts) > 1:
                    # If we have 2 controllers and one of them is
                    # the same as the output, we have a ControlledReplication.
                    # Note that in principle we could generalize this to
                    # more than 2 controllers, but we would need to
                    # define GroupedControlledReplication.
                    # The logic we use here is to remove one controller
                    # matching the output - this is what potentially
                    # replicates. Whatever else is left is considered
                    # a non-matching controller, even if it is actually
                    # an equivalent concept to what replicates: in that
                    # case it is thought of a a controller.
                    removed = False
                    non_matching_controllers = []
                    for controller in controller_concepts:
                        if not removed and \
                                controller.is_equal_to(output_concepts[0],
                                                       with_context=True):
                            removed = True
                        else:
                            non_matching_controllers.append(controller)
                    if len(controller_concepts) == 2 and \
                            len(non_matching_controllers) == 1:
                        yield ControlledReplication(
                            controller=non_matching_controllers[0],
                            subject=output_concepts[0],
                            rate_law=transition_rate,
                            name=transition_id,
                            display_name=transition_name,
                        )
                    else:
                        yield GroupedControlledProduction(
                            controllers=controller_concepts,
                            outcome=output_concepts[0],
                            rate_law=transition_rate,
                            name=transition_id,
                            display_name=transition_name,
                        )
                else:
                    # Check if the controller is the same as the output
                    if controller_concepts[0].is_equal_to(output_concepts[0],
                                                          with_context=True):
                        yield NaturalReplication(
                            subject=output_concepts[0],
                            rate_law=transition_rate,
                            name=transition_id,
                            display_name=transition_name,
                        )
                    else:
                        yield ControlledProduction(
                            controller=controller_concepts[0],
                            outcome=output_concepts[0],
                            rate_law=transition_rate,
                            name=transition_id,
                            display_name=transition_name,
                        )
            else:
                return []

        elif len(controller_concepts) == 1:
            yield ControlledConversion(
                controller=controller_concepts[0],
                subject=input_concepts[0],
                outcome=output_concepts[0],
                rate_law=transition_rate,
                name=transition_id,
                display_name=transition_name,
            )
        else:
            yield GroupedControlledConversion(
                controllers=controller_concepts,
                subject=input_concepts[0],
                outcome=output_concepts[0],
                rate_law=transition_rate,
                display_name=transition_name,
            )


def parameter_to_mira(parameter, param_symbols=None) -> Parameter:
    """
    Return a MIRA parameter from a mapping of MIRA Parameter attributes to
    values.

    Parameters
    ----------
    parameter : Dict[str,Any]
        A mapping containing MIRA Parameter attributes to values.
    param_symbols : Optional[Dict]
        An optional dict of all parameter symbols that are needed if expressions
        are used in parameter distributions so that these can be
        recognized as symbols.

    Returns
    -------
    :
        The corresponding MIRA Parameter.
    """
    distr_json = parameter.get("distribution")
    if distr_json:
        distr_type = distr_json.get("type") if distr_json else None
        # We need to check for symbolic expressions in parameters
        processed_distr_parameters = {}
        for param_key, param_value in distr_json.get("parameters", {}).items():
            if isinstance(param_value, float) or isinstance(param_value, int):
                processed_distr_parameters[param_key] = param_value
            else:
                processed_distr_parameters[param_key] = \
                    safe_parse_expr(param_value)
        distr = Distribution(
            type=distr_type,
            parameters=processed_distr_parameters,
        )
    else:
        distr = None
    data = {
        "name": parameter["id"],
        "display_name": parameter.get("name"),
        "description": parameter.get("description"),
        "value": parameter.get("value"),
        "distribution": distr,
        # Note we handle empty dict below
        "units": parameter.get("units") if parameter.get("units") else None,
    }
    return Parameter.from_json(data)


def get_sympy(expr_data, local_dict=None) -> Optional[sympy.Expr]:
    """Return a sympy expression from a dict with an expression or MathML.

    Sympy string expressions are prioritized over MathML.

    Parameters
    ----------
    expr_data : Dict[str,Any]
        A dict with an expression and/or MathML.
    local_dict : Dict[str, Any]
        A dict of local variables to use when parsing the expression.

    Returns
    -------
    :
        A sympy expression or None if no expression was found.
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
