"""Operations for template models."""

from copy import deepcopy
from collections import defaultdict
import itertools as itt
from typing import Collection, Iterable, List, Mapping, Optional, Set, Tuple, Type, Union

import sympy

from .templates import *

__all__ = [
    "stratify",
    "model_has_grounding",
    "find_models_with_grounding",
    "simplify_rate_laws",
    "aggregate_parameters"
]


def stratify(
    template_model: TemplateModel,
    *,
    key: str,
    strata: Set[str],
    structure: Optional[Iterable[Tuple[str, str]]] = None,
    directed: bool = False,
    conversion_cls: Type[Template] = NaturalConversion,
    cartesian_control: bool = False,
) -> TemplateModel:
    """Multiplies a model into several strata.

    E.g., can turn the SIR model into a two-city SIR model by splitting each concept into
    two derived concepts, each with the context for one of the two cities

    Parameters
    ----------
    template_model :
        A template model
    key :
        The (singular) name of the stratification, e.g., ``"city"``
    strata :
        A list of the values for stratification, e.g., ``["boston", "nyc"]``
    structure :
        An iterable of pairs corresponding to a directed network structure
        where each of the pairs has two strata. If none given, will assume a complete
        network structure. If no structure is necessary, pass an empty list.
    directed :
        Should the reverse direction conversions be added based on the given structure?
    conversion_cls :
        The template class to be used for conversions between strata
        defined by the network structure. Defaults to :class:`NaturalConversion`
    cartesian_control :
        If true, splits all control relationships based on the stratification.

        This should be true for an SIR epidemiology model, the susceptibility to
        infected transition is controlled by infected. If the model is stratified by
        vaccinated and unvaccinated, then the transition from vaccinated
        susceptible population to vaccinated infected populations should be
        controlled by both infected vaccinated and infected unvaccinated
        populations.

        This should be false for stratification of an SIR epidemiology model based
        on cities, since the infected population in one city won't (directly,
        through the perspective of the model) affect the infection of susceptible
        population in another city.

    Returns
    -------
    :
        A stratified template model
    """
    if structure is None:
        structure = list(itt.combinations(strata, 2))
        directed = False

    concept_map = template_model.get_concepts_map()

    templates = []
    for template in template_model.templates:
        # Generate a derived template for each strata
        for stratum in strata:
            templates.append(template.with_context(**{key: stratum}))

    # Generate a conversion between each concept of each strata based on the network structure
    for (source_stratum, target_stratum), concept in itt.product(structure, concept_map.values()):
        subject = concept.with_context(**{key: source_stratum})
        outcome = concept.with_context(**{key: target_stratum})
        # todo will need to generalize for different kwargs for different conversions
        templates.append(conversion_cls(subject=subject, outcome=outcome))
        if not directed:
            templates.append(conversion_cls(subject=outcome, outcome=subject))

    if cartesian_control:
        temp_templates = []
        for template in templates:
            if not isinstance(template, (
                GroupedControlledConversion, GroupedControlledProduction,
                ControlledConversion, ControlledConversion, ControlledProduction
            )):
                temp_templates.append(template)
            else:
                if isinstance(template, (ControlledConversion, ControlledConversion, ControlledProduction)):
                    controllers = [template.controller]
                elif isinstance(template, (GroupedControlledConversion, GroupedControlledProduction)):
                    controllers = list(template.controllers)
                else:
                    raise TypeError
                for stratum in strata:
                    for controller in controllers:
                        s_controller = controller.with_context(**{key: stratum})
                        if not has_controller(template, s_controller):
                            template = template.add_controller(s_controller)

                temp_templates.append(template)
        templates = temp_templates

    return TemplateModel(templates=templates)


def has_controller(template: Template, controller: Concept) -> bool:
    """Check if the template has a controller."""
    if isinstance(template, (GroupedControlledProduction, GroupedControlledConversion)):
        return any(
            c == controller
            for c in template.controllers
        )
    elif isinstance(template, (ControlledProduction, ControlledConversion)):
        return template.controller == controller
    else:
        raise NotImplementedError


def model_has_grounding(template_model: TemplateModel, prefix: str,
                        identifier: str) -> bool:
    """Return whether a model contains a given grounding in any role."""
    search_curie = f'{prefix}:{identifier}'
    for template in template_model.templates:
        for concept in template.get_concepts():
            for concept_prefix, concept_id in concept.identifiers.items():
                if concept_prefix == prefix and concept_id == identifier:
                    return True
            for key, curie in concept.context.items():
                if curie == search_curie:
                    return True
    for key, param in template_model.parameters.items():
        for param_prefix, param_id in param.identifiers.items():
            if param_prefix == prefix and param_id == identifier:
                return True
        for key, curie in param.context.items():
            if curie == search_curie:
                return True
    return False


def find_models_with_grounding(template_models: Mapping[str, TemplateModel],
                               prefix: str, identifier: str) -> Mapping[str, TemplateModel]:
    """Filter a dict of models to ones containing a given grounding in any role."""
    return {k: m for k, m in template_models.items()
            if model_has_grounding(m, prefix, identifier)}


def simplify_rate_laws(template_model: TemplateModel):
    """Return a template model after rewriting templates by simplifying rate laws.

    Parameters
    ----------
    template_model :
        A template model

    Returns
    -------
    :
        A template model with simplified rate laws.
    """
    # Make a copy of the model so that we don't overwrite the original one
    template_model = deepcopy(template_model)
    new_templates = []
    for template in template_model.templates:
        simplified_templates = simplify_rate_law(template,
                                                 template_model.parameters)
        # If we couldn't simplify anything, we just keep the original template
        if simplified_templates is None:
            new_templates.append(template)
        # If simplification resulted in some templates, we add them
        else:
            new_templates += simplified_templates
    template_model.templates = new_templates
    return template_model


def aggregate_parameters(template_model):
    """Return a template model after aggregating parameters for mass-action
    rate laws."""
    template_model = deepcopy(template_model)
    idx = 0
    for template in template_model.templates:
        if not template.rate_law:
            continue
        # 1. Divide the rate law by the mass action rate law sans the parameters
        interactor_rate_law = template.get_interactor_rate_law()
        residual_rate_law = template.rate_law.args[0] / interactor_rate_law
        free_symbols = {s.name for s in residual_rate_law.free_symbols}
        # 2. If what you are left with does not contain any species then
        #    you can aggregate the parameters and create mass action
        # 3. We then need to figure out what to call the new parameter and add
        #    it to the model.
        params_for_subs = {
            k: v.value for k, v in template_model.parameters.items()
        }
        if not (free_symbols & set(template.get_concept_names())):
            residual_rate_law = residual_rate_law.subs(params_for_subs)
            if isinstance(residual_rate_law, (int, float)) or \
                    residual_rate_law.is_Number:
                pvalue = float(residual_rate_law)
                pname = f'mira_param_{idx}'
                template_model.parameters[pname] = \
                    Parameter(name=pname, value=pvalue)
                template.set_mass_action_rate_law(pname)
                idx += 1
        # 4. If the replaced parameters disappear completely then we can remove
        #    them from the model.
    return template_model


def simplify_rate_law(template: Template,
                      parameters: Mapping[str, Parameter]) \
        -> Union[List[Template], None]:
    """Break up a complex template into simpler ones by examining the rate law.

    Parameters
    ----------
    template :
        A template to simplify.
    parameters :
        A dict of parameters in the template model, needed to interpret
        the semantics of rate laws.

    Returns
    -------
    :
        A list of templates, which may be empty if the template could not
    """
    if not isinstance(template, (GroupedControlledConversion,
                                 GroupedControlledProduction)):
        return
    # Make a deepcopy up front so we don't change the original template
    template = deepcopy(template)
    # Start with the sympy.Expr representing the rate law
    rate_law = template.rate_law.args[0]
    new_templates = []
    # We go controller by controller and check if it's controlling the process
    # in a mass-action way.
    for controller in deepcopy(template.controllers):
        # We use a trick here where we take the derivative of the rate law
        # with respect to the controller, and if it takes an expected form
        # we conclue that the controller is controlling the process in a
        # mass-action way and can therefore be spun off.
        controller_rate = sympy.diff(rate_law,
                                     sympy.Symbol(controller.name))
        # We expect the controller rate to only contain the subject
        # and some parameters. It shouldn't contain any symbols that
        # are not one of these
        term_roles = get_term_roles(controller_rate, template,
                                    parameters)
        # This indicates that there are symbols in the controller rate
        # that are unexpected (e.g., the controller itself or some other
        # non-parameter symbol)
        if 'other' in term_roles:
            continue
        new_rate_law = controller_rate * sympy.Symbol(controller.name)
        # In this case, the rate law derivative looks something like
        # parameter * subject
        if isinstance(template, GroupedControlledConversion) and \
                set(term_roles) == {'parameter', 'subject'}:
            new_template = ControlledConversion(
                controller=deepcopy(controller),
                subject=deepcopy(template.subject),
                outcome=deepcopy(template.outcome),
                rate_law=new_rate_law
            )
        # In this case, the rate law derivative contains just the parameter
        elif isinstance(template, GroupedControlledProduction) and \
                set(term_roles) == {'parameter'}:
            new_template = ControlledProduction(
                controller=deepcopy(controller),
                outcome=deepcopy(template.outcome),
                rate_law=new_rate_law
            )
        else:
            continue
        new_templates.append(new_template)
        template.controllers.remove(controller)
        # We simply deduct the mass-action term for the controller
        # from the rate law
        rate_law -= new_rate_law
    # If there are any controllers left in the original template, we keep
    # the template. If not, it means everything was spun off and we can
    # throw away the original template.
    if template.controllers:
        new_templates.append(template)
    return new_templates


def get_term_roles(term, template, parameters):
    """Return terms in a rate law by role."""
    term_roles = defaultdict(list)
    for symbol in term.free_symbols:
        if symbol.name in parameters:
            term_roles['parameter'].append(symbol.name)
        elif isinstance(template, GroupedControlledConversion) and \
                symbol.name == template.subject.name:
            term_roles['subject'].append(symbol.name)
        else:
            term_roles['other'].append(symbol.name)
    return dict(term_roles)
