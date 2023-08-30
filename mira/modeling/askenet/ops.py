import copy
import sympy
from mira.metamodel import SympyExprStr
import mira.metamodel.ops as tmops
from mira.sources.askenet.petrinet import template_model_from_askenet_json
from .petrinet import template_model_to_petrinet_json
from mira.metamodel.io import mathml_to_expression


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
    tm.initials = {
        (new_id if k == old_id else k): v for k, v in tm.initials.items()
    }


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
# rate law is of type Sympy Expression
def replace_rate_law_sympy(tm, transition_id, new_rate_law):
    for template in tm.templates:
        if template.name == transition_id:
            template.rate_law = SympyExprStr(new_rate_law)
    return tm


def replace_rate_law_mathml(tm, transition_id, new_rate_law):
    new_rate_law_sympy = mathml_to_expression(new_rate_law)
    return replace_rate_law_sympy(tm, transition_id, new_rate_law_sympy)


@amr_to_mira
def stratify(*args, **kwargs):
    return tmops.stratify(*args, **kwargs)


@amr_to_mira
def simplify_rate_laws(*args, **kwargs):
    return tmops.simplify_rate_laws(*args, **kwargs)


@amr_to_mira
def aggregate_parameters(*args, **kwargs):
    return tmops.aggregate_parameters(*args, **kwargs)


@amr_to_mira
def counts_to_dimensionless(*args, **kwargs):
    return tmops.counts_to_dimensionless(*args, **kwargs)
