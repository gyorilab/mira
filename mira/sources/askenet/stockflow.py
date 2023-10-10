
"""This module implements parsing Stock and Flow models defined in
https://github.com/DARPA-ASKEM/Model-Representations/tree/main/stockflow.
"""
__all__ = ["template_model_from_stockflow_json"]

import sympy
import requests

from mira.metamodel import *
from mira.modeling.askenet.stockflow import template_model_to_stock_flow_json
from mira.sources.util import get_sympy, transition_to_templates, \
    safe_parse_expr, parameter_to_mira
from mira.modeling import Model

def template_model_from_stockflow_json(model_json) -> TemplateModel:
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

    # Process parameters
    ode_semantics = model_json.get("semantics", {}).get("ode", {})
    mira_parameters = {}
    for parameter in ode_semantics.get('parameters', []):
        mira_parameters[parameter['id']] = parameter_to_mira(parameter)
        symbols[parameter['id']] = sympy.Symbol(parameter['id'])

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
                concept=concepts[initial_state['target']].copy(deep=True),
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
        observable_obj = amr_to_observable(observable, observable_expr)
        tm_observables[observable_obj.name] = observable_obj

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
            and link['source'] not in aux_expressions)]

        input_concepts = [concepts[input].copy(deep=True)]
        output_concepts = [concepts[output].copy(deep=True)]
        controller_concepts = [concepts[i].copy(deep=True) for i in controllers]

        rate_expr = safe_parse_expr(flow['rate_expression'], local_dict=symbols)
        for aux, aux_expr in aux_expressions.items():
            rate_expr = rate_expr.subs(aux, aux_expr)

        templates.extend(
            transition_to_templates(rate_expr,
                                    input_concepts, output_concepts,
                                    controller_concepts, symbols, flow_id, flow_name))


    static_stocks = all_stocks - used_stocks
    for state in static_stocks:
        concept = concepts[state].copy(deep=True)
        templates.append(StaticConcept(subject=concept))

        # Finally, we gather some model-level annotations
    name = model_json.get('header', {}).get('name')
    description = model_json.get('header', {}).get('description')
    anns = Annotations(name=name, description=description)

    return TemplateModel(templates=templates,
                         parameters=mira_parameters,
                         initials=initials,
                         observable=tm_observables,
                         annotations=anns,
                         time=model_time)


def stock_to_concept(stock):
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


def amr_to_observable(observable, observable_expr):
    name = observable['id']
    display_name = observable.get('name')
    description = observable.get('description')
    grounding = observable.get('grounding', {})
    identifiers = grounding.get('identifiers', {})
    context = grounding.get('modifiers', {})
    return Observable(name=name,
                      display_name=display_name,
                      identifiers=identifiers,
                      context=context,
                      description=description,
                      expression=observable_expr)


def main():

    sfamr = requests.get("https://raw.githubusercontent.com/DARPA-ASKEM/Model-Representations/" \
                         "7f5e377225675259baa6486c64102f559edfd79f/stockflow/examples/sir.json").json()
    tm = template_model_from_stockflow_json(sfamr)

    return tm


if __name__ == "__main__":
    tm = main()
