"""This module implements handling flux span model representations that
are the result of stratification and map back to original models
before stratification."""
__all__ = ['reproduce_ode_semantics']

import json
from pathlib import Path

import sympy
from copy import deepcopy
from collections import defaultdict
from mira.metamodel import *
from mira.sources.askenet.petrinet import template_model_from_askenet_json
from mira.modeling import Model
from mira.modeling.askenet.petrinet import AskeNetPetriNetModel


def reproduce_ode_semantics(flux_span):
    """Reproduce ODE semantics from a stratified model (flux span)."""

    # First we make the original template model
    tm = template_model_from_askenet_json(flux_span)

    # We grab the relevant pieces of the flux span structure
    semantics = flux_span['semantics']
    span_1 = semantics['span'][0]
    span_2 = semantics['span'][1]
    model_1 = span_1['system']
    model_2 = span_2['system']
    tm_1 = template_model_from_askenet_json(model_1)
    tm_2 = template_model_from_askenet_json(model_2)
    sem_1 = model_1['semantics']['ode']
    sem_2 = model_2['semantics']['ode']

    # Make sure we have forward and reverse mappings between
    # the original models and the stratified model
    map_1 = dict(span_1['map'])
    map_2 = dict(span_2['map'])
    reverse_map_1 = defaultdict(list)
    reverse_map_2 = defaultdict(list)
    for k, v in map_1.items():
        reverse_map_1[v].append(k)
    for k, v in map_2.items():
        reverse_map_2[v].append(k)

    # We need to be able to look up templates by ID
    template_map = {t.name: t for t in tm.templates}
    template_map_1 = {t.name: t for t in tm_1.templates}
    template_map_2 = {t.name: t for t in tm_2.templates}

    # To handle non-standard transitions we need to also
    # have a transition mapping
    transition_map_1 = {t['id']: t for t in model_1['model']['transitions']}
    transition_map_2 = {t['id']: t for t in model_2['model']['transitions']}

    # If we are missing semantics, we have to make them up
    if not sem_1:
        set_semantics(tm_1, '1')
    if not sem_2:
        set_semantics(tm_2, '2')

    # Deal with parameters
    all_parameters = {}
    all_parameters.update(tm_1.parameters)
    all_parameters.update(tm_2.parameters)

    # Deal with rate laws
    for template in tm.templates:
        # Find what this template is mapped to in the original models
        mapped_1 = map_1[template.name]
        mapped_2 = map_2[template.name]

        # Find the transitions and templates in the original models
        transition_1 = transition_map_1[mapped_1]
        transition_2 = transition_map_2[mapped_2]
        template_1 = template_map_1.get(mapped_1)
        template_2 = template_map_2.get(mapped_2)

        # This happens if the transition is not a standard transition
        # but something like old -> old or old + young -> old + young.
        # We can pragmatically handle these as cases where only an
        # extra parameter needs to be introduced and applied to the
        # joint rate law.
        if not template_1:
            extra_param = f'p_1_{transition_1["id"]}'
        elif not template_2:
            extra_param = f'p_2_{transition_2["id"]}'
        else:
            extra_param = None

        if extra_param:
            all_parameters[extra_param] = Parameter(name=extra_param, value=1.0)

        original_map = map_1 if template_1 else map_2
        original_model = tm_1 if template_1 else tm_2
        original_template = template_1 if template_1 else template_2

        # Find the rate law components in the original model
        rate_law = deepcopy(original_template.rate_law.args[0])
        # Now we need to map states to new states
        concept_names = {c.name for c in template.get_interactors()}
        for concept_name in concept_names:
            # Find the original concept
            original_concept = original_map[concept_name]
            rate_law = rate_law.subs(sympy.Symbol(original_concept),
                                     sympy.Symbol(concept_name))
        if extra_param:
            rate_law *= sympy.Symbol(extra_param)
        template.rate_law = SympyExprStr(rate_law)

    # Deal with observables
    new_observables = {}
    for original_model, reverse_map in zip([tm_1, tm_2],
                                           [reverse_map_1, reverse_map_2]):
        for key, observable in original_model.observables.items():
            expr = deepcopy(observable.expression.args[0])
            for sym in expr.free_symbols:
                mapped_concepts = reverse_map[str(sym)]
                new_expr = sympy.Add(*[sympy.Symbol(c) for c in mapped_concepts])
                expr = expr.subs(sym, new_expr)
            new_observables[key] = Observable(name=key, expression=SympyExprStr(expr))

    # Deal with initial conditions
    new_initial_conditions = {}
    for original_model, reverse_map in zip([tm_1, tm_2],
                                           [reverse_map_1, reverse_map_2]):
        for key, ic in original_model.initials.items():
            concepts = reverse_map[ic.concept.name]
            original_value = ic.value
            for concept in concepts:
                new_initial_conditions[concept] = \
                    Initial(concept=Concept(name=concept),
                            value=original_value/len(concepts))

    # Deal with time
    time = deepcopy(tm_1.time) if tm_1.time else deepcopy(tm_2.time)

    new_tm = TemplateModel(templates=tm.templates,
                           parameters=all_parameters,
                           observables=new_observables,
                           initials=new_initial_conditions,
                           time=time,
                           annotations=deepcopy(tm.annotations))

    new_tm.eliminate_unused_parameters()

    return new_tm


def set_semantics(tm, model_index):
    """Set semantics on a template model."""
    for idx, template in enumerate(tm.templates):
        pname = 'p_%s_%s' % (model_index, idx)
        tm.parameters[pname] = Parameter(name=pname, value=1.0)
        template.set_mass_action_rate_law(pname)


test_file_path = Path(
    __file__
).resolve().parent.parent.parent.parent.joinpath('tests/sir_flux_span.json')
docker_test_file_path = Path("/sw/sir_flux_span.json")


if __name__ == "__main__":
    path = docker_test_file_path if docker_test_file_path.exists() else \
        test_file_path
    with open(path.as_posix()) as fh:
        flux_span = json.load(fh)
    tm = reproduce_ode_semantics(flux_span)
    tm.annotations.name = 'SIR-Two-City-Flux Stratified Model with ODE Semantics'
    tm.annotations.description += ' and then run through MIRA to reconstitute ODE semantics.'
    am = AskeNetPetriNetModel(Model(tm))
    am.to_json_file('sir_flux_span_with_semantics.json')
