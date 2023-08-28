import copy
import sympy
from mira.metamodel import SympyExprStr
import mira.metamodel.ops as tmops
from mira.sources.askenet.petrinet import template_model_from_askenet_json
from .petrinet import template_model_to_petrinet_json


def amr_to_mira(func):
    def wrapper(amr, *args, **kwargs):
        tm = template_model_from_askenet_json(amr)
        result = func(tm, *args, **kwargs)
        amr = template_model_to_petrinet_json(result)
        return amr

    return wrapper


# Edit ID / label / name of State, Transition, Observable, Parameter, Initial
@amr_to_mira
def replace_state_id(tm, old_id, new_id):
    """Replace the ID of a state."""
    concepts_name_map = tm.get_concepts_name_map()
    if old_id not in concepts_name_map:
        raise ValueError(f"State with ID {old_id} not found in model.")
    for template in tm.templates:
        for concept in template.get_concepts():
            if concept.name == old_id:
                concept.name = new_id
        template.rate_law = SympyExprStr(
            template.rate_law.args[0].subs(sympy.Symbol(old_id),
                                           sympy.Symbol(new_id)))
    for observable in tm.observables.values():
        observable.expression = SympyExprStr(
            observable.expression.args[0].subs(sympy.Symbol(old_id),
                                               sympy.Symbol(new_id)))
    for key, initial in copy.deepcopy(tm.initials).items():
        if initial.concept.name == old_id:
            tm.initials[key].concept.name = new_id
            # If the key is same as the old ID, we replace that too
            if key == old_id:
                tm.initials[new_id] = tm.initials.pop(old_id)
    return tm


@amr_to_mira
def replace_transition_id(tm, old_id, new_id):
    """Replace the ID of a transition."""
    for template in tm.templates:
        if template.name == old_id:
            template.name = new_id
    return tm


# As of now, replace_observable_id replaces both 'id' and 'name' field of an observable in output amr
# can possibly add a new argument for display name and set observable.display_name to new argument and then change
# tm to json method to set 'name' field in new_amr['semantics']['ode']['observables'] to observable.display_name
@amr_to_mira
def replace_observable_id(tm, old_id, new_id):
    """Replace the ID of an observable."""
    for obs, observable in copy.deepcopy(tm.observables).items():
        if obs == old_id:
            observable.name = new_id
            tm.observables[new_id] = observable
            tm.observables.pop(old_id)
    return tm


@amr_to_mira
# current bug is that it doesn't return the changed parameter in new_amr['semantics']['ode']['parameters']
# expected 2 returned parameters in list of parameters, only got 1 (the 1 that wasn't changed)
def replace_parameter_id(tm, old_id, new_id):
    """Replace the ID of a parameter."""
    for template in tm.templates:
        if template.rate_law:
            template.rate_law = SympyExprStr(
                template.rate_law.args[0].subs(sympy.Symbol(old_id),
                                               sympy.Symbol(new_id)))
    for observable in tm.observables.values():
        observable.expression = SympyExprStr(
            observable.expression.args[0].subs(sympy.Symbol(old_id),
                                               sympy.Symbol(new_id)))
    return tm


@amr_to_mira
def replace_initial_id(tm, old_id, new_id):
    """Replace the ID of an initial."""
    for init, initial in copy.deepcopy(tm.initials.items()):
        if init == old_id:
            initial.concept.name = new_id
            tm.initials[new_id] = initial
            tm.initials.pop(old_id)
    return tm


# Remove state
@amr_to_mira
def remove_state(tm, state_id):
    new_templates = []
    for template in tm.templates:
        to_remove = False
        for concept in template.get_concepts():
            if concept.name == state_id:
                to_remove = True
        if not to_remove:
            new_templates.append(template)
    tm.templates = new_templates

    for obs, observable in tm.observables.items():
        observable.expression = SympyExprStr(
            observable.expression.args[0].subs(sympy.Symbol(state_id), 0))
    return tm


# Remove transition
@amr_to_mira
def remove_transition(tm, transition_id):
    tm.templates = [t for t in tm.templates if t.name != transition_id]
    return tm


@amr_to_mira
def replace_rate_law_sympy(tm, transition_id, new_rate_law):
    for template in tm.templates:
        if template.name == transition_id:
            template.rate_law = SympyExprStr(new_rate_law)
    return tm


# Replace expression with new Content MathML
# TODO: we need MathML->sympy conversion for this
# def replace_rate_law_mathml(tm, transition_id, new_rate_law):
#    for template in tm.templates:
#        if template.name == transition_id:
#            template.rate_law = SympyExprStr(new_rate_law)
#    return tm


@amr_to_mira
def stratify(**kwargs):
    return tmops.stratify(**kwargs)


@amr_to_mira
def simplify_rate_laws(**kwargs):
    return tmops.simplify_rate_laws(**kwargs)


@amr_to_mira
def aggregate_parameters(**kwargs):
    return tmops.aggregate_parameters(**kwargs)


@amr_to_mira
def counts_to_dimensionless(**kwargs):
    return tmops.counts_to_dimensionless(**kwargs)
