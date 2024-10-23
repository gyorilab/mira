"""This module implements parsing Petri net models defined in
https://github.com/DARPA-ASKEM/Model-Representations/tree/main/petrinet.

MIRA TemplateModel representation limitations to keep in mind:

- Model version not supported
- Model schema not supported
- Initials only have a value, cannot be expressions so information on
  initial condition parameter relationship is lost
"""
__all__ = [
    "model_from_url",
    "model_from_json_file",
    "template_model_from_amr_json",
]

import json
from typing import Optional
from copy import deepcopy

import sympy
import requests

from mira.metamodel import *
from mira.sources.util import get_sympy, transition_to_templates, \
    parameter_to_mira


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
    return template_model_from_amr_json(model_json)


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
    all_states = set()
    for state in model.get('states', []):
        concepts[state['id']] = state_to_concept(state)
        all_states.add(state['id'])

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

    # We first make symbols for all the parameters
    for parameter in ode_semantics.get('parameters', []):
        symbols[parameter['id']] = sympy.Symbol(parameter['id'])

    # We then process the parameters into MIRA Parameter objects
    mira_parameters = {}
    for parameter in ode_semantics.get('parameters', []):
        mira_parameters[parameter['id']] = \
            parameter_to_mira(parameter, param_symbols=symbols)

    # Next we process initial conditions
    initials = {}
    for initial_state in ode_semantics.get("initials", []):
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

    # We get observables from the semantics
    observables = {}
    for observable in ode_semantics.get("observables", []):
        observable_expr = get_sympy(observable, symbols)
        if observable_expr is None:
            continue

        observable = Observable(name=observable['id'],
                                expression=observable_expr,
                                display_name=observable.get('name'))
        observables[observable.name] = observable

    # We get the time variable from the semantics
    time = ode_semantics.get("time")
    if time:
        time_units = time.get('units')
        time_units_expr = get_sympy(time_units, UNIT_SYMBOLS)
        time_units_obj = Unit(expression=time_units_expr) \
            if time_units_expr else None
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
    used_states = set()
    for transition in model.get('transitions', []):
        transition_id = transition['id']  # required, str
        inputs = deepcopy(transition.get('input', []))  # required, Array[str]
        outputs = deepcopy(transition.get('output', []))  # required, Array[str]
        used_states |= (set(inputs) | set(outputs))
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
        input_concepts = [concepts[i].model_copy(deep=True) for i in inputs]
        output_concepts = [concepts[i].model_copy(deep=True) for i in outputs]
        controller_concepts = [concepts[i].model_copy(deep=True) for i in
                               controllers]
        transition_id = transition['id']

        rate_law = get_sympy(rate_obj, local_dict=symbols)
        templates.extend(transition_to_templates(input_concepts,
                                                 output_concepts,
                                                 controller_concepts,
                                                 rate_law,
                                                 transition_id))
    # Handle static states
    static_states = all_states - used_states
    for state in static_states:
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
    description = state.get("description")
    grounding = state.get('grounding', {})
    identifiers = grounding.get('identifiers', {})
    context = grounding.get('modifiers', {})
    units = state.get('units')
    units_expr = get_sympy(units, UNIT_SYMBOLS)
    units_obj = Unit(expression=units_expr) if units_expr else None
    return Concept(name=name,
                   display_name=display_name,
                   description=description,
                   identifiers=identifiers,
                   context=context,
                   units=units_obj)
