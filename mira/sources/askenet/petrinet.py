import json
import sympy
import requests
from mira.metamodel import *


def model_from_url(url):
    """Return a model from a URL"""
    res = requests.get(url)
    model_json = res.json()
    return model_from_json(model_json)


def model_from_json_file(fname):
    """Return a model from a JSON file"""
    with open(fname) as f:
        model_json = json.load(f)
    return model_from_json(model_json)


def model_from_json(model_json):
    """Return a model from a JSON object"""
    # First we build a lookup of states turned into Concepts and then use
    # these as arguments to Templates
    model = model_json['model']
    concepts = {}
    for state in model.get('states', []):
        concepts[state['id']] = state_to_concept(state)

    # Next, we capture all symbols in the model, including states and
    # parameters. We also extract parameters at this point.
    symbols = {state_id: sympy.Symbol(state_id) for state_id in concepts}
    mira_parameters = {}
    for parameter in model.get('parameters', []):
        mira_parameters[parameter['id']] = parameter_to_mira(parameter)
        symbols[parameter['id']] = sympy.Symbol(parameter['id'])

    # Now we iterate over all the transitions and build templates
    templates = []
    for transition in model.get('transitions', []):
        inputs = transition.get('input', [])
        outputs = transition.get('output', [])
        # Since inputs and outputs can contain the same state multiple times
        # and in general we want to preserve the number of times a state
        # appears, we identify controllers one by one, and remove them
        # from the input/output lists
        controllers = []
        both = set(inputs) & set(outputs)
        while both:
            shared = next(iter(both))
            controllers.append(shared)
            inputs.remove(shared)
            outputs.remove(shared)
            both = set(inputs) & set(outputs)
        # We can now get the appropriate concepts for each group
        input_concepts = [concepts[i] for i in inputs]
        output_concepts = [concepts[i] for i in outputs]
        controller_concepts = [concepts[i] for i in controllers]

        templates.extend(transition_to_templates(transition,
                                                 input_concepts,
                                                 output_concepts,
                                                 controller_concepts,
                                                 symbols))
    return TemplateModel(templates=templates,
                         parameters=mira_parameters)


def state_to_concept(state):
    """Return a Concept from a state"""
    name = state['name'] if state.get('name') else state['id']
    grounding = state.get('grounding', {})
    identifiers = grounding.get('identifiers', {})
    context = grounding.get('context', {})
    return Concept(name=name,
                   identifiers=identifiers,
                   context=context)


def parameter_to_mira(parameter):
    """Return a MIRA parameter from a parameter"""
    distr = Distribution(**parameter['distribution']) \
        if parameter.get('distribution') else None
    return Parameter(name=parameter['id'],
                     value=parameter.get('value'),
                     distribution=distr)


def transition_to_templates(transition, input_concepts, output_concepts,
                            controller_concepts, symbols):
    """Return a list of templates from a transition"""
    rate_law_expression = transition.get('rate', {}).get('expression')
    rate_law = \
        sympy.Expr.from_string(rate_law_expression,
                               locals=symbols) if rate_law_expression else None
    if not controller_concepts:
        if not input_concepts:
            for output_concept in output_concepts:
                yield NaturalProduction(outcome=output_concept,
                                        rate_law=rate_law)
        elif not output_concepts:
            for input_concept in input_concepts:
                yield NaturalDegradation(subject=input_concept,
                                         rate_law=rate_law)
        else:
            for input_concept in input_concepts:
                for output_concept in output_concepts:
                    yield NaturalConversion(subject=input_concept,
                                            outcome=output_concept,
                                            rate_law=rate_law)
    else:
        if not (len(input_concepts) == 1 and len(output_concepts) == 1):
            return []
        if len(controller_concepts) == 1:
            yield ControlledConversion(controller=controller_concepts[0],
                                       subject=input_concepts[0],
                                       outcome=output_concepts[0],
                                       rate_law=rate_law)
        else:
            yield GroupedControlledConversion(controllers=controller_concepts,
                                              subject=input_concepts[0],
                                              outcome=output_concepts[0],
                                              rate_law=rate_law)
