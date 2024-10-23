"""This module implements parsing Stock and Flow models defined in
https://github.com/DARPA-ASKEM/Model-Representations/tree/main/stockflow.
"""
__all__ = ["template_model_from_amr_json",
           "stock_to_concept", "model_from_url"]

import sympy
import requests

from mira.metamodel import *
from mira.sources.util import get_sympy, transition_to_templates, \
    safe_parse_expr, parameter_to_mira


def template_model_from_amr_json(model_json) -> TemplateModel:
    """Return a model from a JSON object.

        Parameters
        ----------
        model_json :
            The JSON object.

        Returns
        -------
        :
            A TemplateModel object.
        """
    model = model_json['model']
    stocks = model.get('stocks', [])
    auxiliaries = model.get('auxiliaries', [])
    flows = model.get('flows', [])
    links = model.get('links', [])
    observables = model.get('observables', [])

    # Process stocks
    concepts = {}
    all_stocks = set()
    symbols = {}
    for stock in stocks:
        concept_stock = stock_to_concept(stock)
        concepts[stock['id']] = concept_stock
        all_stocks.add(stock['id'])
        symbols[stock['id']] = sympy.Symbol(stock['id'])

    # Process parameters, first to get all symbols, then
    # processing the parameters to get the MIRA parameters
    ode_semantics = model_json.get("semantics", {}).get("ode", {})
    for parameter in ode_semantics.get('parameters', []):
        symbols[parameter['id']] = sympy.Symbol(parameter['id'])

    mira_parameters = {}
    for parameter in ode_semantics.get('parameters', []):
        mira_parameters[parameter['id']] = \
            parameter_to_mira(parameter, param_symbols=symbols)

    # Process auxiliaries
    aux_expressions = {}
    for auxiliary in auxiliaries:
        aux_expressions[auxiliary['id']] = \
            safe_parse_expr(auxiliary['expression'], local_dict=symbols)
        symbols[auxiliary['id']] = sympy.Symbol(auxiliary['id'])

    initials = {}
    for initial_state in ode_semantics.get('initials', []):
        initial_expr = get_sympy(initial_state, symbols)
        if initial_expr is None:
            continue
        try:
            initial = Initial(
                concept=concepts[initial_state['target']].model_copy(deep=True),
                expression=initial_expr
            )
            initials[initial.concept.name] = initial
        except TypeError:
            continue

    tm_observables = {}
    for observable in observables:
        observable_expr = get_sympy(observable, symbols)
        if observable_expr is None:
            continue
        observable = Observable(name=observable['id'],
                                expression=observable_expr,
                                display_name=observable.get('name'))
        tm_observables[observable.name] = observable

    time = ode_semantics.get("time")
    if time:
        time_units = time.get('units')
        time_units_expr = get_sympy(time_units, UNIT_SYMBOLS)
        time_units_obj = Unit(expression=time_units_expr) \
            if time_units_expr else None
        model_time = Time(name=time['id'], units=time_units_obj)
    else:
        model_time = None

    used_stocks = set()
    templates = []

    for flow in flows:
        flow_id = flow['id']
        flow_name = flow['name']
        # Process flow and links
        input = flow['upstream_stock']
        output = flow['downstream_stock']

        used_stocks |= {input, output}

        # A stock is considered a controller if it has a link to the given
        # flow but is not an input to the flow, and is not an auxiliary
        controllers = [link['source'] for link in links if (
            link['target'] == flow['id']
            and link['source'] != input
            and link['source'] in concepts
            and link['source'] not in aux_expressions)]

        input_concepts = [concepts[input].model_copy(deep=True)] if input \
            else []
        output_concepts = [concepts[output].model_copy(deep=True)] if output else []
        controller_concepts = [concepts[i].model_copy(deep=True) for i in controllers]

        if 'rate_expression' in flow:
            rate_expr = safe_parse_expr(flow['rate_expression'],
                                        local_dict=symbols)
            for aux, aux_expr in aux_expressions.items():
                rate_expr = rate_expr.subs(aux, aux_expr)
        else:
            rate_expr = None

        templates.extend(
            transition_to_templates(
                input_concepts, output_concepts,
                controller_concepts, rate_expr, flow_id, flow_name))

    static_stocks = all_stocks - used_stocks
    for state in static_stocks:
        concept = concepts[state].model_copy(deep=True)
        templates.append(StaticConcept(subject=concept))

        # Finally, we gather some model-level annotations
    name = model_json.get('header', {}).get('name')
    description = model_json.get('header', {}).get('description')

    annotations = model_json.get('metadata', {}).get('annotations', {})
    annotation_attributes = {"name": name, "description": description}
    for key, val in annotations.items():
        # convert list of author names to list of author objects
        if key == "authors":
            val = [Author(name=author_dict["name"]) for author_dict in val]
        annotation_attributes[key] = val

    anns = Annotations(**annotation_attributes)
    return TemplateModel(templates=templates,
                         parameters=mira_parameters,
                         initials=initials,
                         observables=tm_observables,
                         annotations=anns,
                         time=model_time)


def stock_to_concept(stock) -> Concept:
    """Return a Concept from a stock

    Parameters
    ----------
    stock :
        A stock JSON object.

    Returns
    -------
    :
        The Concept corresponding to the provided stock.
    """
    name = stock['id']
    display_name = stock.get('name')
    description = stock.get('description')
    grounding = stock.get('grounding', {})
    identifiers = grounding.get('identifiers', {})
    context = grounding.get('modifiers', {})
    units = stock.get('units')
    units_expr = get_sympy(units, UNIT_SYMBOLS)
    units_obj = Unit(expression=units_expr) if units_expr else None
    return Concept(name=name,
                   display_name=display_name,
                   identifiers=identifiers,
                   context=context,
                   units=units_obj,
                   description=description)


def model_from_url(url: str) -> TemplateModel:
    """Return a model from a URL

    Parameters
    ----------
    url :
        The URL to the JSON file.

    Returns
    -------
    :
        A TemplateModel object.
    """
    res = requests.get(url)
    model_json = res.json()
    return template_model_from_amr_json(model_json)

