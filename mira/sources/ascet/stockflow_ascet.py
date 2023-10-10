import re
import sympy
import requests

from mira.sources.util import get_sympy, transition_to_templates
from mira.modeling.ascet.stockflow_ascet import *


def template_model_from_stockflow_ascet_json(model_json) -> TemplateModel:
    stocks = model_json.get('Stock', [])

    # process stocks/states
    concepts = {}
    all_stocks = set()
    for stock in stocks:
        concept_stock = stock_to_concept(stock)
        concepts[stock['_id']] = concept_stock
        all_stocks.add(stock['_id'])

    symbols, mira_parameters = {}, {}

    # Store stocks as parameters
    for stock_id, concept_item in concepts.items():
        symbols[concept_item.display_name] = \
            sympy.Symbol(concept_item.display_name)

    used_stocks = set()
    flows = model_json['Flow']
    links = model_json['Link']
    templates = []

    for flow in flows:
        # First identify parameters and stocks in the flow expression
        params_in_expr = re.findall(r'p\.([^()*+-/ ]+)', flow['ϕf'])
        stocks_in_expr = re.findall(r'u\.([^()*+-/ ]+)', flow['ϕf'])
        # We can now remove the prefixes from the expression
        expression_str = flow['ϕf'].replace('p.', '').replace('u.', '')

        # Turn each str symbol into a sympy.Symbol and add to dict of symbols
        # if not present before and also turn it into a Parameter object to be
        # added to tm
        for str_symbol in set(params_in_expr + stocks_in_expr):
            if symbols.get(str_symbol) is None:
                symbols[str_symbol] = sympy.Symbol(str_symbol)
                mira_parameters[str_symbol] = \
                    parameter_to_mira({"id": str_symbol})

        # Process flow and links
        # Input stock to the flow is the 'u' field of the flow
        # Output stock of the flow is the 'd' field of the flow
        # Does not handle multiple inputs or outputs of a flow currently
        # Doesn't use copy method as inputs/outputs of stock and flow diagram
        # are non-mutable (e.g. int), not mutable (e.g. lists)
        input = flow['u']
        output = flow['d']
        inputs = []
        outputs = []

        # flow_id or flow_name for template name?
        flow_id = flow['_id']  # required
        flow_name = flow.get('fname')

        inputs.append(input)
        outputs.append(output)

        used_stocks |= (set(inputs) | set(outputs))

        # A stock is considered a controller if it has a link to the given
        # flow but is not an input to the flow
        controllers = [link['s'] for link in links if (
            link['t'] == flow_id and link['s'] != input)]

        input_concepts = [concepts[i].copy(deep=True) for i in inputs]
        output_concepts = [concepts[i].copy(deep=True) for i in outputs]
        controller_concepts = [concepts[i].copy(deep=True) for i in controllers]

        templates.extend(
            transition_to_templates({'expression': expression_str},
                                    input_concepts, output_concepts,
                                    controller_concepts, symbols, flow_id, flow_name))

    static_stocks = all_stocks - used_stocks

    for state in static_stocks:
        concept = concepts[state].copy(deep=True)
        templates.append(StaticConcept(subject=concept))

    return TemplateModel(templates=templates,
                         parameters=mira_parameters)


def stock_to_concept(state):
    name = state['_id']
    display_name = state.get('sname')
    grounding = state.get('grounding', {})
    identifiers = grounding.get('identifiers', {})
    context = grounding.get('modifiers', {})
    units = state.get('units')
    units_expr = get_sympy(units, UNIT_SYMBOLS)
    units_obj = Unit(expression=units_expr) if units_expr else None
    return Concept(name=name,
                   display_name=display_name,
                   identifiers=identifiers,
                   context=context,
                   units=units_obj)


def parameter_to_mira(parameter):
    """Return a MIRA parameter from a parameter"""
    distr = Distribution(**parameter['distribution']) \
        if parameter.get('distribution') else None
    data = {
        "name": parameter['id'],
        "display_name": parameter.get('name'),
        "description": parameter.get('description'),
        "value": parameter.get('value'),
        "distribution": distr,
        "units": parameter.get('units')
    }
    return Parameter.from_json(data)


def main():
    sfamr = requests.get(
        'https://raw.githubusercontent.com/AlgebraicJulia/'
        'py-acsets/jpfairbanks-patch-1/src/acsets/schemas/'
        'examples/StockFlowp.json').json()
    tm = template_model_from_stockflow_ascet_json(sfamr)
    sf_ascet = template_model_to_stockflow_ascet_json(tm)
    return tm


if __name__ == "__main__":
    tm = main()
