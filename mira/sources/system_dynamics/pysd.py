"""This module implements parsing of a generic pysd model irrespective of source and source type
and extracting its contents to create an equivalent MIRA template model.
"""
__all__ = ["template_model_from_pysd_model"]

import re

import pandas as pd
import sympy

from mira.metamodel import *
from mira.metamodel.utils import safe_parse_expr
from mira.metamodel import Concept, TemplateModel
from mira.sources.util import (
    parameter_to_mira,
    transition_to_templates,
    get_sympy,
)

CONTROL_VARIABLE_NAMES = {
    "FINALTIME",
    "INITIALTIME",
    "SAVEPER",
    "TIMESTEP",
    "FINAL TIME",
    "INITIAL TIME",
    "TIME STEP",
}
UNITS_MAPPING = {
    sympy.Symbol("Person"): sympy.Symbol("person"),
    sympy.Symbol("Persons"): sympy.Symbol("person"),
    sympy.Symbol("Day"): sympy.Symbol("day"),
    sympy.Symbol("Days"): sympy.Symbol("day"),
}
SYMPY_FLOW_RATE_PLACEHOLDER = safe_parse_expr("xxplaceholderxx")


def template_model_from_pysd_model(pysd_model, expression_map) -> TemplateModel:
    """Given a model and its accompanying expression_map, extract information from the arguments
    to create an equivalent MIRA template model.

    Parameters
    ----------
    pysd_model : Model
        The pysd model object
    expression_map : dict[str,str]
        Map of variable name to expression

    Returns
    -------
    :
        MIRA template model
    """
    # dataframe that contains information about each variable in the model
    model_doc_df = pysd_model.doc

    state_initial_values = pysd_model.state
    processed_expression_map = {}

    # Mapping of variable name in vensim model to variable python-equivalent name
    old_name_new_pyname_map = dict(
        zip(model_doc_df["Real Name"], model_doc_df["Py Name"])
    )

    # preprocess expression text to make it sympy parseable
    for var_name, var_expression in expression_map.items():
        new_var_name = old_name_new_pyname_map[var_name]
        processed_expression_map[new_var_name] = preprocess_expression_text(
            var_expression
        )

    # Mapping of variable's python name to symbol for expression parsing
    symbols = dict(
        zip(
            model_doc_df["Py Name"],
            list(map(lambda x: sympy.Symbol(x), model_doc_df["Py Name"])),
        )
    )

    # Retrieve the states
    model_states = model_doc_df.loc[
        (model_doc_df["Type"] == "Stateful")
        & (model_doc_df["Subtype"] == "Integ")
    ]

    concepts = {}
    all_states = set()

    # map between states and incoming/out-coming rate laws
    state_rate_map = {}

    # process states and build mapping of state to input rate laws and output rate laws
    for index, state in model_states.iterrows():
        concept_state = state_to_concept(state)
        concepts[concept_state.name] = concept_state
        all_states.add(concept_state.name)
        symbols[concept_state.name] = sympy.Symbol(concept_state.name)

        state_name = state["Py Name"]
        state_rate_map[state_name] = {"input_rates": [], "output_rates": []}
        state_expr_text = processed_expression_map[state_name]

        # retrieve the expression of inflows and outflows for the state
        state_arg_sympy = safe_parse_expr(state_expr_text, symbols)

        # Create a map of states and whether the flows involved with a state are going in
        # or out of the state
        if state_arg_sympy.args:
            # if it's just the negation of a single symbol
            if (
                sympy.core.numbers.NegativeOne() in state_arg_sympy.args
                and len(state_arg_sympy.args) == 2
            ):
                str_symbol = str(state_arg_sympy)
                state_rate_map[state_name]["output_rates"].append(
                    str_symbol[1:]
                )
            else:
                for rate_free_symbol in state_arg_sympy.args:
                    str_rate_free_symbol = str(rate_free_symbol)
                    if "-" in str_rate_free_symbol:
                        # If the symbol representing the flow has a negative sign, it is an
                        # outgoing flow
                        # Add the symbol to outputs symbol without the negative sign
                        state_rate_map[state_name]["output_rates"].append(
                            str_rate_free_symbol[1:]
                        )
                    else:
                        state_rate_map[state_name]["input_rates"].append(
                            str_rate_free_symbol
                        )
        else:
            # if it's just a single symbol (i.e. no negation), args property will be empty
            state_rate_map[state_name]["input_rates"].append(
                str(state_arg_sympy)
            )

    # process initials, currently we use the value of the state at timestamp 0
    mira_initials = {}
    for state_initial_value, (state_name, state_concept) in zip(
        state_initial_values, concepts.items()
    ):
        # if the state value is not a number
        if not isinstance(state_initial_value, int) and not isinstance(
            state_initial_value, float
        ):
            initial = Initial(
                concept=concepts[state_name].copy(deep=True),
                expression=SympyExprStr("0"),
            )
        else:
            initial = Initial(
                concept=concepts[state_name].copy(deep=True),
                expression=SympyExprStr(sympy.Float(state_initial_value)),
            )
        mira_initials[initial.concept.name] = initial

    # Stella issue
    # Currently cannot capture all parameters as some of them cannot have their expressions parsed
    # Additionally, some auxiliary variables are added as parameters due to inability to parse
    # the auxiliary expression and differentiate it from a parameter
    mira_parameters = {}
    # process parameters
    # No discernible way to identify only parameters in model_doc_df, so go through all variables
    # in the processed expression map
    for name, expression in processed_expression_map.items():
        # Stella issue
        # Sometimes parameter values reference a stock rather than a number
        # Current placeholder for incorrectly constructed parameter expressions is "-1"
        try:
            eval_expression = safe_parse_expr(expression).evalf()
        except TypeError:
            eval_expression = safe_parse_expr("0")

        str_eval_expression = str(eval_expression)
        value = None
        is_initial = False
        if str_eval_expression in mira_initials:
            value = float(str(mira_initials[str_eval_expression].expression))
            is_initial = True

        # Stella issue
        # Replace negative signs for placeholder parameter value for Aux structures
        # that cannot be parsed
        if str_eval_expression in mira_initials or (
            eval_expression != SYMPY_FLOW_RATE_PLACEHOLDER
            and str_eval_expression.replace(".", "")
            .replace(" ", "")
            .replace("-", "")
            .isdecimal()
        ):
            if not is_initial:
                value = float(str_eval_expression)
            model_parameter_info = model_doc_df[model_doc_df["Py Name"] == name]
            if (
                model_parameter_info["Units"].values[0]
                and model_parameter_info["Units"].values[0] != "dimensionless"
            ):
                unit_text = (
                    model_parameter_info["Units"].values[0].replace(" ", "")
                )
                parameter = {
                    "id": name,
                    "value": value,
                    "description": model_parameter_info["Comment"].values[0],
                    "units": {"expression": unit_text},
                }
            else:
                parameter = {
                    "id": name,
                    "value": value,
                    "description": model_parameter_info["Comment"].values[0],
                }

            mira_parameters[name] = parameter_to_mira(parameter)

            # standardize parameter units if they exist
            if mira_parameters[name].units:
                param_unit = mira_parameters[name].units
                for old_unit_symbol, new_unit_symbol in UNITS_MAPPING.items():
                    param_unit.expression = param_unit.expression.subs(
                        old_unit_symbol, new_unit_symbol
                    )
    # construct transitions mapping that determine inputs and outputs states to a rate-law
    transition_map = {}
    rates = []
    for m in state_rate_map.values():
        for input_rates in m["input_rates"]:
            rates.append(input_rates)
        for output_rates in m["output_rates"]:
            rates.append(output_rates)

    # create map of transitions
    for rate_name in rates:
        inputs, outputs, controllers, rate_expr = [], [], [], None
        for state_name, in_out_rate_map in state_rate_map.items():
            # if a rate cannot be parsed, assign None
            # This is a Stella issue as some expressions aren't created properly
            try:
                rate_expr = safe_parse_expr(
                    processed_expression_map[rate_name],
                    symbols,
                )
            except TypeError:
                rate_expr = SYMPY_FLOW_RATE_PLACEHOLDER
            if rate_name in in_out_rate_map["output_rates"]:
                inputs.append(state_name)
            if rate_name in in_out_rate_map["input_rates"]:
                outputs.append(state_name)
                if (
                    sympy.Symbol(state_name) in rate_expr.free_symbols
                    and rate_name
                    not in state_rate_map[state_name]["output_rates"]
                ):
                    controllers.append(state_name)
        transition_map[rate_name] = {
            "name": rate_name,
            "expression": rate_expr,
            "inputs": inputs,
            "outputs": outputs,
            "controllers": controllers,
        }

    used_states = set()

    # Create templates from transitions
    templates_ = []
    for template_id, (transition_name, transition) in enumerate(
        transition_map.items()
    ):
        input_concepts, input_names = [], []
        output_concepts, output_names = [], []
        controller_concepts = []

        for input_name in transition.get("inputs"):
            input_concepts.append(concepts[input_name].copy(deep=True))
            input_names.append(input_name)

        for output_name in transition.get("outputs"):
            output_concepts.append(concepts[output_name].copy(deep=True))
            output_names.append(output_name)

        for controller_name in transition.get("controllers"):
            controller_concepts.append(
                concepts[controller_name].copy(deep=True)
            )

        used_states.update(input_names, output_names)

        templates_.extend(
            transition_to_templates(
                input_concepts=input_concepts,
                output_concepts=output_concepts,
                controller_concepts=controller_concepts,
                transition_rate=transition["expression"]
                if transition["expression"] != SYMPY_FLOW_RATE_PLACEHOLDER
                else None,
                transition_id=str(template_id + 1),
                transition_name=transition_name,
            )
        )

    return TemplateModel(
        templates=templates_,
        parameters=mira_parameters,
        initials=mira_initials,
    )


def state_to_concept(state) -> Concept:
    """Create a MIRA Concept from a state

    Parameters
    ----------
    state : pd.Series
        The series that contains state data

    Returns
    -------
    :
        The MIRA concept created from the state
    """
    name = state["Py Name"]
    description = state["Comment"]
    unit_dict = {
        "expression": state["Units"].replace(" ", "")
        if state["Units"]
        else None
    }
    unit_expr = get_sympy(unit_dict, UNIT_SYMBOLS)
    units_obj = Unit(expression=unit_expr) if unit_expr else None

    return Concept(name=name, units=units_obj, description=description)


def preprocess_expression_text(expr_text):
    """Preprocess a string expression to convert the expression into sympy parseable string

    Parameters
    ----------
    expr_text : str
        The string expression

    Returns
    -------
    : str
        The processed string expression
    """

    if not expr_text:
        return expr_text

    # TODO: Use regular expressions for all text preprocessing rather than using replace
    # TODO: Account for symbols used as operands in expressions
    # Remove spaces between non-alphanumeric (which represent variables or numbers) characters
    expr_text = re.sub(
        r"(?<=[^\w\s])\s+(?=[^\w\s])|(?<=[^\w\s])\s+(?=\w)|(?<=\w)\s+(?=[^\w\s])",
        "",
        expr_text,
    )

    # strip leading and trailing white spaces
    # remove spaces between operators and operands
    # replace space between two words that makeup a variable name with "_"'
    expr_text = (
        expr_text.strip()
        .replace(" * ", "*")
        .replace(" - ", "-")
        .replace(" / ", "/")
        .replace(" + ", "+")
        .replace("^", "**")
        .replace(" ", "_")
        .replace("'", "")
        .replace('"', "")
        .lower()
    )
    return expr_text
