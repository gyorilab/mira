"""This module implements parsing Petri net models defined in
https://github.com/DARPA-ASKEM/Model-Representations/tree/main/petrinet.

MIRA TemplateModel representation limitations to keep in mind:
- Model version not supported
- Model schema not supported
- Initials only have a value, cannot be expressions so information on
  initial condition parameter relationship is lost
"""
__all__ = ["model_from_url", "model_from_json_file", "template_model_from_askenet_json"]

import json

import sympy
import requests

from mira.metamodel import *


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
    return template_model_from_askenet_json(model_json)


def model_from_json_file(fname: str) -> TemplateModel:
    """Return a model from a JSON file.

    Parameters
    ----------
    fname :
        The path to the JSON file.

    Returns
    -------
    :
        A TemplateModel object.
    """
    with open(fname) as f:
        model_json = json.load(f)
    return template_model_from_askenet_json(model_json)


def template_model_from_askenet_json(model_json) -> TemplateModel:
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
    # First we build a lookup of states turned into Concepts and then use
    # these as arguments to Templates
    # Top level structure of model as of
    # https://github.com/DARPA-ASKEM/Model-Representations/pull/24
    # {
    #   "states": [state, ...],
    #   "transitions": [transition, ...],
    # }
    model = model_json['model']
    concepts = {}
    for state in model.get('states', []):
        concepts[state['id']] = state_to_concept(state)

    # Next, we capture all symbols in the model, including states and
    # parameters. We also extract parameters at this point.
    # Top level structure of semantics > ode as of Model-Representations PR24:
    # {
    #   "rates": [...],
    #   "initials": [...],
    #   "parameters": [...],
    # }
    #
    # Each parameter is of the form:
    # {
    #   "id": "parameter_id",
    #   "description": "parameter description",
    #   "value": 1.0,
    #   "grounding": {...},
    #   "distribution": {...},
    # }
    ode_semantics = model_json.get("semantics", {}).get("ode", {})
    symbols = {state_id: sympy.Symbol(state_id) for state_id in concepts}
    mira_parameters = {}
    for parameter in ode_semantics.get('parameters', []):
        mira_parameters[parameter['id']] = parameter_to_mira(parameter)
        symbols[parameter['id']] = sympy.Symbol(parameter['id'])

    param_values = {
        p['id']: p['value'] for p in ode_semantics.get('parameters', [])
        if p.get('value') is not None
    }

    # Next we process initial conditions
    initials = {}
    for initial_state in ode_semantics.get("initials", []):
        initial_expression = initial_state.get("expression")
        if initial_expression:
            initial_sympy = safe_parse_expr(initial_expression,
                                            local_dict=symbols)
            initial_sympy = initial_sympy.subs(param_values)
            try:
                initial_val = float(initial_sympy)
            except TypeError:
                continue

            initial = Initial(
                concept=concepts[initial_state['target']].copy(deep=True),
                value=initial_val
            )
            initials[initial.concept.name] = initial

    # We get observables from the semantics
    observables = {}
    for observable in ode_semantics.get("observables", []):
        observable_expression = observable.get("expression")
        if observable_expression:
            observable_sympy = safe_parse_expr(observable_expression,
                                               local_dict=symbols)
            observable = Observable(name=observable['id'],
                                    expression=observable_sympy)
            observables[observable.name] = observable

    # We get the time variable from the semantics
    time = ode_semantics.get("time")
    if time:
        time_units = time.get('units')
        time_units_obj = None
        if time_units:
            time_expr = time_units.get('expression')
            time_units_expr = safe_parse_expr(time_expr,
                                              local_dict=UNIT_SYMBOLS)
            time_units_obj = Unit(expression=time_units_expr)
        model_time = Time(name=time['id'], units=time_units_obj)
    else:
        model_time = None

    # Now we iterate over all the transitions and build templates
    # As of https://github.com/DARPA-ASKEM/Model-Representations/pull/24
    # each transition have the following structure:
    # {
    #   "id": "id1",
    #   "input": [...],
    #   "output": [...],
    #   "grounding": {...},  # In /$defs/grounding
    #   "properties": {...},  # In /$defs/properties

    # Get the rates by their target, the target here refers to a transition id
    rates = {
        rate['target']: rate for rate in ode_semantics.get('rates', [])
    }
    templates = []
    # Loop
    for transition in model.get('transitions', []):
        transition_id = transition['id']  # required, str
        inputs = transition.get('input', [])  # required, Array[str]
        outputs = transition.get('output', [])  # required, Array[str]
        transition_grounding = transition.get('grounding', {})  # optional, Object
        transition_properties = transition.get('properties', {})  # optional, Object
        rate_obj = rates.get(transition_id, {})  # optional, Object

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
        input_concepts = [concepts[i].copy(deep=True) for i in inputs]
        output_concepts = [concepts[i].copy(deep=True) for i in outputs]
        controller_concepts = [concepts[i].copy(deep=True) for i in controllers]

        templates.extend(transition_to_templates(rate_obj,
                                                 input_concepts,
                                                 output_concepts,
                                                 controller_concepts,
                                                 symbols))

    # Finally, we gather some model-level annotations
    name = model_json.get('name')
    description = model_json.get('description')
    anns = Annotations(name=name, description=description)
    return TemplateModel(templates=templates,
                         parameters=mira_parameters,
                         initials=initials,
                         annotations=anns,
                         observables=observables,
                         time=model_time)


def state_to_concept(state):
    """Return a Concept from a state"""
    # Structure of state as of
    # https://github.com/DARPA-ASKEM/Model-Representations/pull/24
    # {
    #   "id": "id1",  # required, not the same as `identifier1` in grounding
    #   "name": "name1",
    #   "grounding": {
    #     "identifiers": {
    #       "identifier key": "identifier value",
    #     },
    #     "modifiers": {
    #       "context key": "context value",
    #     }
    #   }
    # }
    # Note that in the shared representation we have id and name
    # whereas for Concepts in MIRA we have names and display
    # names
    name = state['id']
    display_name = state.get('name')
    grounding = state.get('grounding', {})
    identifiers = grounding.get('identifiers', {})
    context = grounding.get('modifiers', {})
    units = state.get('units')
    units_obj = None
    if units:
        # TODO: if sympy expression isn't given, parse MathML
        expr = units.get('expression')
        if expr:
            units_expr = safe_parse_expr(expr, local_dict=UNIT_SYMBOLS)
            units_obj = Unit(expression=units_expr)
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
        "value": parameter.get('value'),
        "distribution": distr,
        "units": parameter.get('units')
    }
    return Parameter.from_json(data)


def transition_to_templates(transition_rate, input_concepts, output_concepts,
                            controller_concepts, symbols):
    """Return a list of templates from a transition"""
    rate_law_expression = transition_rate.get('expression')
    rate_law = safe_parse_expr(rate_law_expression,
                               local_dict=symbols) \
        if rate_law_expression else None
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
