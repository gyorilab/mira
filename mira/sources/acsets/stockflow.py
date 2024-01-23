"""This module implements parsing of a Stock and Flow acset model and turns it into a MIRA
template models.
"""

import sympy

from mira.metamodel import (
    TemplateModel,
    safe_parse_expr,
    StaticConcept,
    UNIT_SYMBOLS,
    Unit,
    Concept,
)
from mira.sources.util import (
    get_sympy,
    transition_to_templates,
    parameter_to_mira,
    revert_parseable_expression,
)


def is_number(number):
    """If a character is a number, return true, else return false

    Parameters
    ----------
    number : str
        The character to be tested

    Returns
    -------
    : bool
    """
    try:
        float_num = float(number)
        return True
    except ValueError:
        return False


def template_model_from_stockflow_ascet_json(model_json) -> TemplateModel:
    """Returns a TemplateModel by processing a Stock and flow JSON dict.

    Parameters
    ----------
    model_json : JSON
        The stock and flow JSON structure.

    Returns
    -------
    :
        A TemplateModel extracted from the Stock and flow model.
    """
    stocks = model_json.get("Stock", [])

    concepts, symbols, mira_parameters, reverse_parse_map = {}, {}, {}, {}
    all_stocks = set()
    stock_name_set = set()

    # process stocks/states
    # Store stocks as symbols and add their initial stock as a parameter
    for stock in stocks:
        concept_stock = stock_to_concept(stock)
        concepts[stock["_id"]] = concept_stock
        all_stocks.add(stock["_id"])
        stock_name_set.add(concept_stock.display_name)
        symbols[concept_stock.display_name] = sympy.Symbol(
            concept_stock.display_name
        )

    used_stocks = set()
    flows = model_json["Flow"]
    links = model_json["Link"]
    templates = []

    for flow in flows:
        expression_str = flow["ϕf"]

        # current expr contains symbols with substitute string
        # for example p.beta (not sympy parseable as a string) -> pXX_XXbeta (sympy parseable as
        # a string) is now a in the expression string and thus a free symbol in the expression

        # stock names are already processed and added to the dict of symbols, thus we don't have
        # to do any substitution for previously unparseable stock names (e.g. u.S)
        expr = safe_parse_expr(expression_str, symbols)

        # get the parameters (operands that aren't a stock or a number) in the flow expression
        params_in_expr = [
            old_param_symbol
            for old_param_symbol in expr.free_symbols
            if str(old_param_symbol) not in stock_name_set
            and not is_number(str(old_param_symbol))
        ]

        # Substitute the changed parseable free symbol (pXX_XXbeta) for the original free symbol
        # (p.beta)
        for old_param_symbol in params_in_expr:
            if old_param_symbol not in reverse_parse_map:
                reverse_parse_map[old_param_symbol] = sympy.Symbol(
                    revert_parseable_expression(str(old_param_symbol))
                )

        for old_symbol, new_symbol in reverse_parse_map.items():
            expr = expr.subs(old_symbol, new_symbol)

        # If the string symbol representing a mira parameter extracted from the rate law is not in
        # the dict of parameters,
        # add the string symbol to the dict of symbols and turn it into a parameter object
        for param_symbol in reverse_parse_map.values():
            str_symbol = str(param_symbol)
            if mira_parameters.get(str_symbol) is None:
                symbols[str_symbol] = param_symbol
                mira_parameters[str_symbol] = parameter_to_mira(
                    {"id": str_symbol, "display_name": str_symbol}
                )

        # Process flow and links
        # Input stock to the flow is the 'u' field of the flow
        # Output stock of the flow is the 'd' field of the flow
        # Does not handle multiple inputs or outputs of a flow currently
        # Doesn't use copy method as inputs/outputs of stock and flow diagram
        # are non-mutable (e.g. int), not mutable (e.g. lists)
        input = flow["u"]
        output = flow["d"]
        inputs = []
        outputs = []

        # flow_id or flow_name for template name?
        flow_id = flow["_id"]  # required
        flow_name = flow.get("fname")

        inputs.append(input)
        outputs.append(output)

        used_stocks |= set(inputs) | set(outputs)

        # A stock is considered a controller if it has a link to the given
        # flow but is not an input to the flow
        controllers = [
            link["s"]
            for link in links
            if (link["t"] == flow_id and link["s"] != input)
        ]

        input_concepts = [concepts[i].copy(deep=True) for i in inputs]
        output_concepts = [concepts[i].copy(deep=True) for i in outputs]
        controller_concepts = [concepts[i].copy(deep=True) for i in controllers]

        expression_sympy = safe_parse_expr(expression_str, symbols)

        templates.extend(
            transition_to_templates(
                input_concepts,
                output_concepts,
                controller_concepts,
                expression_sympy,
                flow_id,
                flow_name,
            )
        )

    static_stocks = all_stocks - used_stocks

    for state in static_stocks:
        concept = concepts[state].copy(deep=True)
        templates.append(StaticConcept(subject=concept))

    return TemplateModel(templates=templates, parameters=mira_parameters)


def stock_to_concept(stock) -> Concept:
    """Creates a concept from a stock

    Parameters
    ----------
    stock : JSON
        The stock to be converted

    Returns
    -------
    :
        The concept created from the stock
    """
    name = stock["_id"]
    display_name = stock.get("sname")
    grounding = stock.get("grounding", {})
    identifiers = grounding.get("identifiers", {})
    context = grounding.get("modifiers", {})
    units = stock.get("units")
    units_expr = get_sympy(units, UNIT_SYMBOLS)
    units_obj = Unit(expression=units_expr) if units_expr else None
    return Concept(
        name=name,
        display_name=display_name,
        identifiers=identifiers,
        context=context,
        units=units_obj,
    )
