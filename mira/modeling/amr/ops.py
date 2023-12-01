import copy
from functools import wraps

import sympy
from mira.metamodel import SympyExprStr, Unit
import mira.metamodel.ops as tmops
from mira.sources.amr.petrinet import template_model_from_amr_json
from .petrinet import template_model_to_petrinet_json
from mira.metamodel.io import mathml_to_expression
from mira.metamodel.template_model import Parameter, Distribution, Observable, \
    Initial, Concept
from mira.metamodel.templates import NaturalConversion, NaturalProduction, \
    NaturalDegradation, StaticConcept
from typing import Mapping


def amr_to_mira(func):
    @wraps(func)
    def wrapper(amr, *args, **kwargs):
        tm = template_model_from_amr_json(amr)
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
def replace_observable_id(tm, old_id, new_id, name=None):
    """Replace the ID and display name (optional) of an observable"""
    for obs, observable in copy.deepcopy(tm.observables).items():
        if obs == old_id:
            observable.name = new_id
            observable.display_name = name if name else observable.display_name
            tm.observables[new_id] = observable
            tm.observables.pop(old_id)
    return tm


@amr_to_mira
def remove_observable(tm, removed_id):
    """Remove an observable from the template model"""
    for obs, observable in copy.deepcopy(tm.observables).items():
        if obs == removed_id:
            tm.observables.pop(obs)
    return tm


@amr_to_mira
def remove_parameter(tm, removed_id, replacement_value=None):
    """
    Substitute every instance of the parameter with the given replacement_value.
    If replacement_value is none, substitute the parameter with 0.
    """
    if replacement_value:
        tm.substitute_parameter(removed_id, replacement_value)
    else:
        tm.eliminate_parameter(removed_id)

    for initial in tm.initials.values():
        if replacement_value:
            initial.substitute_parameter(removed_id, replacement_value)
        else:
            initial.substitute_parameter(removed_id, 0)
    return tm


@amr_to_mira
def add_observable(tm, new_id, new_name, new_expression):
    """Add a new observable object to the template model"""
    # Note that if an observable already exists with the given
    # key, it will be replaced
    rate_law_sympy = mathml_to_expression(new_expression)
    new_observable = Observable(name=new_id, display_name=new_name,
                                expression=rate_law_sympy)
    tm.observables[new_id] = new_observable
    return tm


@amr_to_mira
def replace_parameter_id(tm, old_id, new_id):
    """Replace the ID of a parameter"""
    if old_id not in tm.parameters:
        raise ValueError(f"Parameter with ID {old_id} not found in model.")
    for template in tm.templates:
        if template.rate_law:
            template.rate_law = SympyExprStr(
                template.rate_law.args[0].subs(sympy.Symbol(old_id),
                                               sympy.Symbol(new_id)))
    for observable in tm.observables.values():
        observable.expression = SympyExprStr(
            observable.expression.args[0].subs(sympy.Symbol(old_id),
                                               sympy.Symbol(new_id)))
    for key, param in copy.deepcopy(tm.parameters).items():
        if param.name == old_id:
            popped_param = tm.parameters.pop(param.name)
            popped_param.name = new_id
            tm.parameters[new_id] = popped_param

    for initial in tm.initials.values():
        if initial.expression:
            initial.substitute_parameter(old_id, sympy.Symbol(new_id))

    return tm


@amr_to_mira
def add_parameter(tm, parameter_id: str,
                  name: str = None,
                  description: str = None,
                  value: float = None,
                  distribution=None,
                  units_mathml: str = None):
    """Add a new parameter to the template model"""
    tm.add_parameter(parameter_id, name, description, value, distribution, units_mathml)
    return tm


@amr_to_mira
def replace_initial_id(tm, old_id, new_id):
    """Replace the ID of an initial."""
    tm.initials = {
        (new_id if k == old_id else k): v for k, v in tm.initials.items()
    }
    return tm


# Remove state
@amr_to_mira
def remove_state(tm, state_id):
    """Remove a state from the template model"""
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


@amr_to_mira
def add_state(tm, state_id: str, name: str = None,
              units_mathml: str = None, grounding: Mapping[str, str] = None,
              context: Mapping[str, str] = None):
    """Add a new state to the template model"""
    if units_mathml:
        units = Unit(expression=SympyExprStr(mathml_to_expression(units_mathml)))
    else:
        units = None

    new_concept = Concept(name=state_id,
                          display_name=name,
                          identifiers=grounding,
                          context=context,
                          units=units,
                          )
    static_template = StaticConcept(subject=new_concept)
    tm.templates.append(static_template)
    return tm


@amr_to_mira
def remove_transition(tm, transition_id):
    """Remove a transition object from the template model"""
    tm.templates = [t for t in tm.templates if t.name != transition_id]
    return tm


@amr_to_mira
def add_transition(tm, new_transition_id, src_id=None, tgt_id=None,
                   rate_law_mathml=None, params_dict: Mapping = None):
    """Add a new transition to the template model

       Parameters
       ----------
       tm:
           The template model
       new_transition_id:
           The ID of the new transition to add
       src_id:
           The ID of the subject of the newly created transition (default None)
       tgt_id:
           The ID of the outcome of the newly created transition (default None)
        rate_law_math_ml:
            The rate law associated with the newly created transition
        params_dict:
            A mapping of parameter attributes to their respective values if the user
            decides to explicitly create parameters
       Returns
       -------
       :
            The updated template model object
        """
    if src_id is None and tgt_id is None:
        ValueError("You must pass in at least one of source and target id")
    if src_id not in tm.get_concepts_name_map() and tgt_id not in tm.get_concepts_name_map():
        ValueError("At least src_id or tgt_id must correspond to an existing concept in the template model")
    rate_law_sympy = SympyExprStr(mathml_to_expression(rate_law_mathml)) \
        if rate_law_mathml else None

    subject_concept = tm.get_concepts_name_map().get(src_id)
    outcome_concept = tm.get_concepts_name_map().get(tgt_id)

    tm = tm.add_transition(transition_name=new_transition_id,
                           subject_concept=subject_concept,
                           outcome_concept=outcome_concept,
                           rate_law_sympy=rate_law_sympy,
                           params_dict=params_dict)
    return tm


@amr_to_mira
def replace_rate_law_sympy(tm, transition_id, new_rate_law: sympy.Expr):
    """Replace the rate law of transition. The new rate law passed in will be a sympy.Expr object"""
    # NOTE: this assumes that a sympy expression object is given
    # though it might make sense to take a string instead
    for template in tm.templates:
        if template.name == transition_id:
            template.rate_law = SympyExprStr(new_rate_law)
    return tm


# This function isn't wrapped because it calls a wrapped function and just
# passes the AMR through
def replace_rate_law_mathml(amr, transition_id, new_rate_law):
    """Replace the rate law of a transition. The new rate law passed in will be a MathML str object"""
    new_rate_law_sympy = mathml_to_expression(new_rate_law)
    return replace_rate_law_sympy(amr, transition_id, new_rate_law_sympy)


@amr_to_mira
def replace_observable_expression_sympy(tm, obs_id,
                                        new_expression_sympy: sympy.Expr):
    """Replace the expression of an observable. The new rate law passed in will be a sympy.Expr object"""
    for obs, observable in tm.observables.items():
        if obs == obs_id:
            observable.expression = SympyExprStr(new_expression_sympy)
    return tm


@amr_to_mira
def replace_initial_expression_sympy(tm, initial_id,
                                     new_expression_sympy: sympy.Expr):
    """Replace the expression of an initial. The new rate law passed in will be a sympy.Expr object"""
    for init, initial in tm.initials.items():
        if init == initial_id:
            initial.expression = SympyExprStr(new_expression_sympy)
    return tm


# This function isn't wrapped because it calls a wrapped function and just
# passes the AMR through
def replace_observable_expression_mathml(amr, obs_id, new_expression_mathml):
    """Replace the expression of an observable. The new rate law passed in will be MathML str object"""
    new_expression_sympy = mathml_to_expression(new_expression_mathml)
    return replace_observable_expression_sympy(amr, obs_id,
                                               new_expression_sympy)


# This function isn't wrapped because it calls a wrapped function and just
# passes the AMR through
def replace_initial_expression_mathml(amr, initial_id, new_expression_mathml):
    """Replace the expression of an initial. The new rate law passed in will be a MathML str object"""
    new_expression_sympy = mathml_to_expression(new_expression_mathml)
    return replace_initial_expression_sympy(amr, initial_id,
                                            new_expression_sympy)


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
