from typing import Optional
import sympy
import requests

from mira.metamodel import *
from mira.metamodel.utils import safe_parse_expr


def template_model_from_sf_json(model_json) -> TemplateModel:
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
        symbols[concept_item.display_name] = sympy.Symbol(concept_item.display_name)

        param_data = {"id": str(stock_id),
                      "name": concept_item.display_name}
        mira_parameters[concept_item.display_name] = parameter_to_mira(param_data)

    used_stocks = set()
    flows = model_json['Flow']
    links = model_json['Link']
    templates = []

    for flow in flows:
        # Process expression associated with a flow and extract parameters

        # Remove markers 'p.' and 'u.' from expression
        expression_str = flow['ϕf'].replace('p.', '').replace('u.', '')
        processed_expression_str = expression_str
        delimiters = ["+", "/", "-", "*", '(', ')',
                      '1', '2', '3', '4', '5', '6', '7', '8', '9']

        # Remove all non-symbols from an expression by splitting on every delimiter in list
        for delimiter in delimiters:
            processed_expression_str = " ".join(processed_expression_str.split(delimiter))

        # Create a list of where each element is a str symbol
        str_symbol_list = processed_expression_str.split()

        for str_symbol in str_symbol_list:
            symbols[str_symbol] = sympy.Symbol(str_symbol)
            if mira_parameters.get(str_symbol) is None:
                mira_parameters[str_symbol] = parameter_to_mira({"id": str_symbol})

        # Process flow and links
        input = flow['u']
        output = flow['d']

        # flow_id or flow_name for template name?
        flow_id = flow['_id']  # required
        flow_name = flow.get('fname')

        input_link = links[input - 1]
        output_link = links[output - 1]
        inputs = []
        outputs = []

        inputs.append(input)
        outputs.append(output)

        used_stocks |= (set(inputs) | set(outputs))
        controllers = []

        # Logic is most likely not generalizable to other stock and flow models
        if (flow['u'] != output and output_link['t'] == flow['_id'] and input_link['t'] == output_link['t'] and
            output_link['s'] != flow['_id']):

            controllers.append(output_link['_id'])

        input_concepts = [concepts[i].copy(deep=True) for i in inputs]
        output_concepts = [concepts[i].copy(deep=True) for i in outputs]
        controller_concepts = [concepts[i].copy(deep=True) for i in controllers]

        templates.extend(flow_to_template(expression_str, input_concepts, output_concepts,
                                          controller_concepts, symbols, flow_id))

    static_stocks = all_stocks - used_stocks

    for state in static_stocks:
        concept = concepts[state].copy(deep=True)
        templates.append(StaticConcept(subject=concept))

    return TemplateModel(templates=templates,
                         parameters=mira_parameters)


def flow_to_template(flow_rate, input_concepts, output_concepts, controller_concepts,
                     symbols, flow_id):
    rate_law = safe_parse_expr(flow_rate, symbols)
    if not controller_concepts:
        if not input_concepts:
            for output_concept in output_concepts:
                yield NaturalProduction(outcome=output_concept,
                                        rate_law=rate_law,
                                        name=flow_id)
        elif not output_concepts:
            for input_concept in input_concepts:
                yield NaturalDegradation(subject=input_concept,
                                         rate_law=rate_law,
                                         name=flow_id)
        else:
            for input_concept in input_concepts:
                for output_concept in output_concepts:
                    yield NaturalConversion(subject=input_concept,
                                            outcome=output_concept,
                                            rate_law=rate_law,
                                            name=flow_id)
    else:
        if not (len(input_concepts) == 1 and len(output_concepts) == 1):
            if len(input_concepts) == 1 and not output_concepts:
                if len(controller_concepts) > 1:
                    yield GroupedControlledDegradation(controllers=controller_concepts,
                                                       subject=input_concepts[0],
                                                       rate_law=rate_law,
                                                       name=flow_id)
                else:
                    yield ControlledDegradation(controller=controller_concepts[0],
                                                subject=input_concepts[0],
                                                rate_law=rate_law,
                                                name=flow_id)
            elif len(output_concepts) == 1 and not input_concepts:
                if len(controller_concepts) > 1:
                    yield GroupedControlledProduction(controllers=controller_concepts,
                                                      outcome=output_concepts[0],
                                                      rate_law=rate_law,
                                                      name=flow_id)
                else:
                    yield ControlledProduction(controller=controller_concepts[0],
                                               outcome=output_concepts[0],
                                               rate_law=rate_law,
                                               name=flow_id)
            else:
                return []

        elif len(controller_concepts) == 1:
            yield ControlledConversion(controller=controller_concepts[0],
                                       subject=input_concepts[0],
                                       outcome=output_concepts[0],
                                       rate_law=rate_law,
                                       name=flow_id)
        else:
            yield GroupedControlledConversion(controllers=controller_concepts,
                                              subject=input_concepts[0],
                                              outcome=output_concepts[0],
                                              rate_law=rate_law)


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


def get_sympy(expr_data, local_dict=None) -> Optional[sympy.Expr]:
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
        'py-acsets/jpfairbanks-patch-1/src/acsets/schemas/examples/StockFlowp.json').json()
    tm = template_model_from_sf_json(sfamr)


if __name__ == "__main__":
    main()
