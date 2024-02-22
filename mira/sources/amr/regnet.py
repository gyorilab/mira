"""This module implements parsing RegNet models defined in
https://github.com/DARPA-ASKEM/Model-Representations/tree/main/regnet.
"""
__all__ = ["model_from_url", "model_from_json_file", "template_model_from_amr_json"]


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
    # First we build a lookup of vertices turned into Concepts and then use
    # these as arguments to Templates. Vertices can also have natural
    # production/degradation rates, which we capture here.
    model = model_json['model']
    concepts = {}
    templates = []
    for vertex in model.get('vertices', []):
        concepts[vertex['id']] = vertex_to_concept(vertex)
        template = vertex_to_template(vertex, concepts[vertex['id']])
        if template:
            templates.append(template)

    # Next, we capture all symbols in the model, including states and
    # parameters. We also extract parameters at this point.
    symbols = {state_id: sympy.Symbol(state_id) for state_id in concepts}
    mira_parameters = {}
    for parameter in model.get('parameters', []):
        mira_parameters[parameter['id']] = parameter_to_mira(parameter)
        symbols[parameter['id']] = sympy.Symbol(parameter['id'])

    param_values = {p['id']: p['value'] for p in model.get('parameters', [])}

    # Next we process initial conditions
    initials = {}
    for vertex in model.get('vertices', []):
        initial_expression = vertex.get('initial')
        if isinstance(initial_expression, str):
            initial_sympy = safe_parse_expr(initial_expression,
                                            local_dict=symbols)
        elif isinstance(initial_expression, (int, float)):
            initial_sympy = sympy.sympify(initial_expression)
        else:
            continue
        initial = Initial(concept=concepts[vertex['id']],
                          expression=initial_sympy)
        initials[initial.concept.name] = initial

    # Now we iterate over all the transitions and build templates
    for transition in model.get('edges', []):
        source = transition['source']
        target = transition['target']
        source_concept = concepts[source]
        target_concept = concepts[target]
        if transition['sign'] is True:
            template = ControlledReplication(
                controller=source_concept,
                subject=target_concept
            )
        else:
            template = ControlledDegradation(
                controller=source_concept,
                subject=target_concept
            )
        props = transition.get('properties', {})
        rate_constant = props.get('rate_constant')
        if rate_constant is not None:
            template.set_mass_action_rate_law(rate_constant)
        templates.append(template)
    # Finally, we gather some model-level annotations
    name = model_json.get('header', {}).get('name')
    description = model_json.get('header', {}).get('description')
    anns = Annotations(name=name, description=description)
    return TemplateModel(templates=templates,
                         parameters=mira_parameters,
                         initials=initials,
                         annotations=anns)


def vertex_to_concept(vertex):
    """Return a Concept from a vertex"""
    name = vertex['name'] if vertex.get('name') else vertex['id']
    grounding = vertex.get('grounding', {})
    identifiers = grounding.get('identifiers', {})
    context = grounding.get('context', {})
    return Concept(name=name,
                   identifiers=identifiers,
                   context=context)


def vertex_to_template(vertex, concept):
    rate_constant = vertex.get('rate_constant')
    sign = vertex.get('sign')
    if rate_constant is None:
        return None
    if sign is True:
        template = NaturalReplication(subject=concept)
    else:
        template = NaturalDegradation(subject=concept)
    template.set_mass_action_rate_law(rate_constant)
    return template


def parameter_to_mira(parameter):
    """Return a MIRA parameter from a parameter"""
    distr = Distribution(**parameter['distribution']) \
        if parameter.get('distribution') else None
    return Parameter(name=parameter['id'],
                     value=parameter.get('value'),
                     distribution=distr)
