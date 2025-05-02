"""Operations for template models."""
import logging
from copy import deepcopy
from collections import defaultdict
import itertools as itt
from typing import Callable, Collection, Iterable, List, Mapping, Optional, \
    Tuple, Type, Union

import sympy

from .template_model import TemplateModel, Initial, Parameter, Observable
from .templates import *
from .units import Unit
from .utils import SympyExprStr

__all__ = [
    "stratify",
    "simplify_rate_laws",
    "check_simplify_rate_laws",
    "aggregate_parameters",
    "get_term_roles",
    "counts_to_dimensionless",
    "deactivate_templates",
    "add_observable_pattern",
]


logger = logging.getLogger(__name__)


def stratify(
    template_model: TemplateModel,
    key: str,
    strata: Collection[str],
    strata_curie_to_name: Optional[Mapping[str, str]] = None,
    strata_name_lookup: bool = False,
    structure: Optional[Iterable[Tuple[str, str]]] = None,
    directed: bool = False,
    conversion_cls: Type[Template] = NaturalConversion,
    cartesian_control: bool = False,
    modify_names: bool = True,
    params_to_stratify: Optional[Collection[str]] = None,
    params_to_preserve: Optional[Collection[str]] = None,
    concepts_to_stratify: Optional[Collection[str]] = None,
    concepts_to_preserve: Optional[Collection[str]] = None,
    param_renaming_uses_strata_names: Optional[bool] = False,
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
        or ``[geonames:4930956, geonames:5128581]``.
    strata_curie_to_name :
        If provided, should map from a key used in ``strata`` to a name.
        For example, ``{"geonames:4930956": "boston",
        "geonames:5128581": "nyc"}``.
    strata_name_lookup :
        If true, will try to look up the entity names of the strata values
        under the assumption that they are curies. This flag has no impact
        if ``strata_curie_to_name`` is given.
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
    modify_names :
        If true, will modify the names of the concepts to include the strata
        (e.g., ``"S"`` becomes ``"S_boston"``). If false, will keep the original
        names.
    params_to_stratify :
        A list of parameters to stratify. If none given, will stratify all
        parameters.
    params_to_preserve :
        A list of parameters to preserve. If none given, will stratify all
        parameters.
    concepts_to_stratify :
        A list of concepts to stratify. If none given, will stratify all
        concepts.
    concepts_to_preserve :
        A list of concepts to preserve. If none given, will stratify all
        concepts.
    param_renaming_uses_strata_names :
        If true, the strata names will be used in the parameter renaming.
        If false, the strata indices will be used. Default: False
    Returns
    -------
    :
        A stratified template model
    """
    if strata_name_lookup and strata_curie_to_name is None:
        from mira.dkg.web_client import get_entities_web, MissingBaseUrlError
        try:
            entity_map = {e.id: e.name for e in get_entities_web(strata)}
            # Update the mapping with the strata values that are missing from
            # the map
            strata_curie_to_name = {s: entity_map.get(s, s) for s in strata}
        except MissingBaseUrlError as err:
            logger.warning(
                "Web client not available, cannot look up strata names",
                exc_info=True
            )

    if structure is None:
        structure = list(itt.combinations(strata, 2))
        # directed = False  # TODO: What's the function of this? Commented
        #  out, the stratification works well for the directed case,
        #  e.g. unvaccinated -> vaccinated.

    concept_map = template_model.get_concepts_map()
    concept_names_map = template_model.get_concepts_name_map()
    concept_names = set(concept_names_map.keys())

    # List of new templates
    templates = []

    # Figure out excluded concepts
    if concepts_to_stratify is None:
        if concepts_to_preserve is None:
            exclude_concepts = set()
        else:
            exclude_concepts = set(concepts_to_preserve)
    else:
        if concepts_to_preserve is None:
            exclude_concepts = concept_names - set(concepts_to_stratify)
        else:
            exclude_concepts = set(concepts_to_preserve) | (
                concept_names - set(concepts_to_stratify)
            )

    stratum_index_map = {stratum: i for i, stratum in enumerate(strata)}

    keep_unstratified_parameters = set()
    all_param_mappings = defaultdict(set)
    for template in template_model.templates:
        # If the template doesn't have any concepts that need to be stratified
        # then we can just keep it as is and skip the rest of the loop
        if not set(template.get_concept_names()) - exclude_concepts:
            original_params = template.get_parameter_names()
            for param in original_params:
                keep_unstratified_parameters.add(param)
            templates.append(deepcopy(template))
            continue

        # Check if we will have any controllers in the template
        controllers = template.get_controllers()
        stratified_controllers = [c for c in controllers if c.name
                                  not in exclude_concepts]
        ncontrollers = len(stratified_controllers)

        # If we have controllers, and we want cartesian control then
        # we will stratify controllers separately
        stratify_controllers = (ncontrollers > 0) and cartesian_control

        # Generate a derived template for each stratum
        for stratum, stratum_idx in stratum_index_map.items():
            template_strata = []
            new_template = deepcopy(template)
            new_template.name = \
                f"{template.name if template.name else 't'}_{stratum}"
            # We have to make sure that we only add the stratum to the
            # list of template strata if we stratified any of the non-controllers
            # in this first for loop
            any_noncontrollers_stratified = False
            # We apply this stratum to each concept except for controllers
            # in case we will separately stratify those
            for concept in new_template.get_concepts_flat(
                    exclude_controllers=stratify_controllers,
                    refresh=True):
                if concept.name in exclude_concepts:
                    continue
                concept.with_context(
                    do_rename=modify_names,
                    curie_to_name_map=strata_curie_to_name,
                    inplace=True,
                    **{key: stratum})
                any_noncontrollers_stratified = True

            # If we don't stratify controllers then we are done and can just
            # make the new rate law, then append this new template
            if not stratify_controllers:
                # We only need to do this if we stratified any of the non-controllers
                if any_noncontrollers_stratified:
                    template_strata = [stratum if
                                       param_renaming_uses_strata_names else stratum_idx]
                    param_mappings = rewrite_rate_law(template_model=template_model,
                                                      old_template=template,
                                                      new_template=new_template,
                                                      template_strata=template_strata,
                                                      params_to_stratify=params_to_stratify,
                                                      params_to_preserve=params_to_preserve)
                    for old_param, new_param in param_mappings.items():
                        all_param_mappings[old_param].add(new_param)
                templates.append(new_template)
            # Otherwise we are stratifying controllers separately
            else:
                # Use itt.product to generate all combinations of
                # strata for controllers. For example, if there
                # are two controllers A and B and stratification is into
                # old, middle, and young, then there will be the following 9:
                #    (A_old, B_old), (A_old, B_middle), (A_old, B_young),
                #    (A_middle, B_old), (A_middle, B_middle), (A_middle, B_young),
                #    (A_young, B_old), (A_young, B_middle), (A_young, B_young)
                for c_strata_tuple in itt.product(strata, repeat=ncontrollers):
                    stratified_template = deepcopy(new_template)
                    stratified_controllers = stratified_template.get_controllers()
                    # Filter to make sure we skip controllers that are excluded
                    stratified_controllers = [c for c in stratified_controllers
                                              if c.name not in exclude_concepts]
                    template_strata = [stratum if param_renaming_uses_strata_names
                                       else stratum_idx]
                    # We now apply the stratum assigned to each controller in this particular
                    # tuple to the controller
                    for controller, c_stratum in zip(stratified_controllers, c_strata_tuple):
                        if controller.name in exclude_concepts:
                            continue
                        stratified_template.name += f"_{c_stratum}"
                        controller.with_context(do_rename=modify_names, inplace=True,
                                                **{key: c_stratum})
                        template_strata.append(c_stratum if param_renaming_uses_strata_names
                                               else stratum_index_map[c_stratum])

                    # Wew can now rewrite the rate law for this stratified template,
                    # then append the new template
                    param_mappings = rewrite_rate_law(template_model=template_model,
                                                      old_template=template,
                                                      new_template=stratified_template,
                                                      template_strata=template_strata,
                                                      params_to_stratify=params_to_stratify,
                                                      params_to_preserve=params_to_preserve)
                    for old_param, new_param in param_mappings.items():
                        all_param_mappings[old_param].add(new_param)
                    templates.append(stratified_template)

    # Handle initial values and expressions depending on different
    # criteria
    initials = {}
    param_value_mappings = {}
    for initial_key, initial in template_model.initials.items():
        # We need to keep track of whether we stratified any parameters in
        # the expression for this initial and if the parameter is being
        # replaced by multiple stratified parameters
        any_param_stratified = False
        param_replacements = defaultdict(set)

        for stratum_idx, stratum in enumerate(strata):
            # Figure out if the concept for this initial is one that we
            # need to stratify or not
            if (exclude_concepts and initial.concept.name in exclude_concepts) or \
                    (concepts_to_preserve and initial.concept.name in concepts_to_preserve):
                # Just make a copy of the original initial concept
                new_concept = deepcopy(initial.concept)
                concept_stratified = False
            else:
                # We create a new concept for the given stratum
                new_concept = initial.concept.with_context(
                    do_rename=modify_names,
                    curie_to_name_map=strata_curie_to_name,
                    **{key: stratum},
                )
                concept_stratified = True
            # Now we may have to rewrite the expression so that we can
            # update for stratified parameters so we make a copy and figure
            # out what parameters are in the expression
            new_expression = deepcopy(initial.expression)
            init_expr_params = template_model.get_parameters_from_expression(
                new_expression.args[0]
            )
            template_strata = [stratum if
                               param_renaming_uses_strata_names else stratum_idx]
            for parameter in init_expr_params:
                # If a parameter is explicitly listed as one to preserve, then
                # don't stratify it
                if params_to_preserve is not None and parameter in params_to_preserve:
                    continue
                # If we have an explicit stratification list then if something isn't
                # in the list then don't stratify it.
                elif params_to_stratify is not None and parameter not in params_to_stratify:
                    continue
                # Otherwise we go ahead with stratification, i.e., in cases
                # where nothing was said about parameter stratification or the
                # parameter was listed explicitly to be stratified
                else:
                    # We create a new parameter symbol for the given stratum
                    param_suffix = '_'.join([str(s) for s in template_strata])
                    new_param = f'{parameter}_{param_suffix}'
                    any_param_stratified = True
                    all_param_mappings[parameter].add(new_param)
                    # We need to update the new, stratified parameter's value
                    # to be the original parameter's value divided by the number
                    # of strata
                    param_value_mappings[new_param] = \
                        template_model.parameters[parameter].value / len(strata)
                    # If the concept is not stratified then we have to replace
                    # the original parameter with the sum of stratified ones
                    # so we just keep track of that in a set
                    if not concept_stratified:
                        param_replacements[parameter].add(new_param)
                    # Otherwise we have to rewrite the expression to use the
                    # new parameter as replacement for the original one
                    else:
                        new_expression = new_expression.subs(parameter,
                                                             sympy.Symbol(new_param))

            # If we stratified any parameters in the expression then we have
            # to update the initial value expression to reflect that
            if any_param_stratified:
                if param_replacements:
                    for orig_param, new_params in param_replacements.items():
                        new_expression = new_expression.subs(
                            orig_param,
                            sympy.Add(*[sympy.Symbol(np) for np in new_params])
                        )
                new_initial = new_expression
            # Otherwise we can just use the original expression, except if the
            # concept was stratified, then we have to divide the initial
            # expression into as many parts as there are strata
            else:
                if concept_stratified:
                    new_initial = SympyExprStr(new_expression.args[0] / len(strata))
                else:
                    new_initial = new_expression

            initials[new_concept.name] = \
                Initial(concept=new_concept, expression=new_initial)

    parameters = {}

    for parameter_key, parameter in template_model.parameters.items():
        if parameter_key not in all_param_mappings:
            parameters[parameter_key] = parameter
            continue
        # We need to keep the original param if it has been broken
        # up but not in every instance. We then also
        # generate the counted parameter variants
        elif parameter_key in keep_unstratified_parameters:
            parameters[parameter_key] = parameter
        # We otherwise generate variants of the parameter based
        # on the previously complied parameter mappings
        for stratified_param in all_param_mappings[parameter_key]:
            d = deepcopy(parameter)
            d.name = stratified_param
            if stratified_param in param_value_mappings:
                d.value = param_value_mappings[stratified_param]
            parameters[stratified_param] = d

    observables = {}
    for observable_key, observable in template_model.observables.items():
        syms = {s.name for s in observable.expression.args[0].free_symbols}
        expr = deepcopy(observable.expression.args[0])
        for sym in (syms & concept_names) - exclude_concepts:
            new_symbols = []
            for stratum in strata:
                new_concept = concept_names_map[sym].with_context(
                    do_rename=modify_names,
                    curie_to_name_map=strata_curie_to_name,
                    **{key: stratum},
                )
                new_symbols.append(sympy.Symbol(new_concept.name))
            expr = expr.subs(sympy.Symbol(sym), sympy.Add(*new_symbols))
        observables[observable_key] = deepcopy(observable)
        observables[observable_key].expression = SympyExprStr(expr)

    # Generate a conversion between each concept of each strata based on the network structure
    for idx, ((source_stratum, target_stratum), concept) in \
            enumerate(itt.product(structure, concept_map.values())):
        if concept.name in exclude_concepts:
            continue
        # Get stratum names from map if provided, otherwise use the stratum
        source_stratum_name = strata_curie_to_name.get(
            source_stratum, source_stratum
        ) if strata_curie_to_name else source_stratum
        target_stratum_name = strata_curie_to_name.get(
            target_stratum, target_stratum
        ) if strata_curie_to_name else target_stratum
        param_name = f"p_{source_stratum_name}_{target_stratum_name}"
        if param_name not in parameters:
            parameters[param_name] = Parameter(name=param_name, value=0.1)
        subject = concept.with_context(do_rename=modify_names,
                                       curie_to_name_map=strata_curie_to_name,
                                       **{key: source_stratum})
        outcome = concept.with_context(do_rename=modify_names,
                                       curie_to_name_map=strata_curie_to_name,
                                       **{key: target_stratum})
        # todo will need to generalize for different kwargs for different conversions
        template = conversion_cls(subject=subject, outcome=outcome,
                                  name=f't_conv_{idx}_{source_stratum_name}_{target_stratum_name}')
        template.set_mass_action_rate_law(param_name)
        templates.append(template)
        if not directed:
            param_name = f"p_{target_stratum_name}_{source_stratum_name}"
            if param_name not in parameters:
                parameters[param_name] = Parameter(name=param_name, value=0.1)
            reverse_template = conversion_cls(subject=outcome, outcome=subject,
                                              name=f't_conv_{idx}_{target_stratum_name}_{source_stratum_name}')
            reverse_template.set_mass_action_rate_law(param_name)
            templates.append(reverse_template)

    # We replicate the unused parameters to be stratified into all the strata
    if params_to_stratify:
        all_params = set(template_model.parameters)
        used_params = template_model.get_all_used_parameters()
        # There can be certain parameters that were stratified and then removed
        # so we have to check the intersection of currently existing parameters
        # and ones to stratify to find unused ones
        unused_params_to_stratify = (all_params & set(params_to_stratify)) - used_params
        for param in unused_params_to_stratify:
            for stratum in strata:
                param_suffix = stratum if param_renaming_uses_strata_names \
                    else str(stratum_index_map[stratum])
                new_param_name = f'{param}_{param_suffix}'
                new_param = deepcopy(template_model.parameters[param])
                new_param.name = new_param_name
                parameters[new_param_name] = new_param
            parameters.pop(param, None)

    new_model = TemplateModel(templates=templates,
                              parameters=parameters,
                              initials=initials,
                              observables=observables,
                              annotations=deepcopy(template_model.annotations),
                              time=template_model.time)
    # We do this so that any subsequent stratifications will
    # be agnostic to previous ones
    new_model.reset_base_names()
    return new_model


def rewrite_rate_law(
    template_model: TemplateModel,
    old_template: Template,
    new_template: Template,
    template_strata: List[int],
    params_to_stratify: Optional[Collection[str]] = None,
    params_to_preserve: Optional[Collection[str]] = None,
):
    """Rewrite the rate law of a template based on a new template.

    This function is used in the context of stratification.

    Parameters
    ----------
    template_model :
        The unstratified template model containing the templates.
    old_template :
        The original template.
    new_template :
        The new template. One of the templates created by stratification of
        ``old_template``.
    template_strata :
        A list of strata indices that have been applied to the template,
        used for parameter naming.
    params_to_stratify :
        A list of parameters to stratify. If none given, will stratify all
        parameters.
    params_to_preserve :
        A list of parameters to preserve. If none given, will stratify all
        parameters.
    """
    # Rewrite the rate law by substituting new symbols corresponding
    # to the stratified controllers in for the originals
    rate_law = old_template.rate_law
    if not rate_law:
        return {}

    # If the template has controllers/subjects that affect the rate law
    # and there is an overlap between these, then simple substitution
    # can be problematic.
    has_subject_controller_overlap = False
    if has_controller(old_template) and has_subject(old_template):
        if old_template.subject.name in {c.name for c in
                                         old_template.get_controllers()}:
            has_subject_controller_overlap = True

    # Step 1. Rename controllers
    for old_controller, new_controller in zip(
        old_template.get_controllers(), new_template.get_controllers(),
    ):
        # Here, if we have subject/controller overlap, we can't use subs
        # otherwise something like x * x will get replaced in a single
        # substitution. Assuming that the controller is a mass-action-like
        # factor here, we can divide the rate law by the old controller and
        # multiply by the new controller. This ensures that only a single
        # instance of the old controller is replaced by the new controller.
        if has_subject_controller_overlap and \
                old_controller.name == old_template.subject.name:
            rate_law = rate_law.args[0] / sympy.Symbol(old_controller.name)
            rate_law *= sympy.Symbol(new_controller.name)
            rate_law = SympyExprStr(rate_law)
        # If there is no overlap issue, we can use subs
        else:
            rate_law = rate_law.subs(
                sympy.Symbol(old_controller.name),
                sympy.Symbol(new_controller.name),
            )

    # Step 2. Rename subject and object
    old_cbr = old_template.get_concepts_by_role()
    new_cbr = new_template.get_concepts_by_role()
    if "subject" in old_cbr and "subject" in new_cbr:
        rate_law = rate_law.subs(
            sympy.Symbol(old_template.subject.name),
            sympy.Symbol(new_template.subject.name),
        )
    if "outcome" in old_cbr and "outcome" in new_cbr:
        rate_law = rate_law.subs(
            sympy.Symbol(old_template.outcome.name),
            sympy.Symbol(new_template.outcome.name),
        )

    # Step 3. Rename parameters by generating new parameters
    # named according to the strata that were applied to the
    # given template
    parameters = list(template_model.get_parameters_from_rate_law(rate_law))
    param_mappings = {}
    for parameter in parameters:
        # If a parameter is explicitly listed as one to preserve, then
        # don't stratify it
        if params_to_preserve is not None and parameter in params_to_preserve:
            continue
        # If we have an explicit stratification list then if something isn't
        # in the list then don't stratify it.
        elif params_to_stratify is not None and parameter not in params_to_stratify:
            continue
        # Otherwise we go ahead with stratification, i.e., in cases
        # where nothing was said about parameter stratification or the
        # parameter was listed explicitly to be stratified
        else:
            param_suffix = '_'.join([str(s) for s in template_strata])
            new_param = f'{parameter}_{param_suffix}'
            param_mappings[parameter] = new_param
            rate_law = rate_law.subs(parameter, sympy.Symbol(new_param))

    new_template.rate_law = rate_law
    return param_mappings


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


def check_simplify_rate_laws(template_model: TemplateModel) -> \
        Mapping[str, Union[str, int, TemplateModel]]:
    """Return a summary of what changes upon rate law simplification

    Parameters
    ----------
    template_model :
        A template model

    Returns
    -------
    :
        A dictionary with the result of the check under the `result` key.
        The result can be one of the following:
        - {'result': 'NO_GROUP_CONTROLLERS'}: If there are no templates with
           grouped controllers
        - {'result': 'NO_CHANGE'}: If the model does contain templates with
           grouped controllers but simplification does not change the model.
        - {'result': 'NO_CHANGE_IN_MAX_CONTROLLERS',
           'max_controller_count': n}: If the model is simplified but the
           maximum number of controllers remains the same so it might not be
           worth doing the simplification. In this case the max controller
           count in the model is returned. The simplified model
           itself is also returned.
        - {'result': 'MEANINGFUL_CHANGE',
           'max_controller_decrease': n}: If the model is simplified and the
           maximum number of controllers also meaningfully changes. In this
           case the decrease in the maximum controller count is returned.
           The simplified model itself is also returned.
    """
    if not any(isinstance(template, (GroupedControlledConversion,
                                     GroupedControlledProduction,
                                     GroupedControlledDegradation))
               for template in template_model.templates):
        return {'result': 'NO_GROUP_CONTROLLERS'}
    simplified_model = simplify_rate_laws(template_model)
    old_template_count = len(template_model.templates)
    new_template_count = len(simplified_model.templates)
    if old_template_count == new_template_count:
        return {'result': 'NO_CHANGE'}

    def max_controller_count(template_model):
        max_count = 0
        for template in template_model.templates:
            if hasattr(template, 'controllers'):
                max_count = max(len(template.get_controllers()), max_count)
            elif hasattr(template, 'controller'):
                max_count = max(1, max_count)
        return max_count

    old_max_count = max_controller_count(template_model)
    new_max_count = max_controller_count(simplified_model)
    if old_max_count == new_max_count:
        return {'result': 'NO_CHANGE_IN_MAX_CONTROLLERS',
                'max_controller_count': old_max_count,
                'simplified_model': simplified_model}
    return {'result': 'MEANINGFUL_CHANGE',
            'max_controller_decrease': old_max_count - new_max_count,
            'simplified_model': simplified_model}


def aggregate_parameters(template_model: TemplateModel) -> TemplateModel:
    """Return a template model after aggregating parameters for mass-action
    rate laws.

    Parameters
    ----------
    template_model :
        A template model whose rate laws will be aggregated.

    Returns
    -------
    :
        A template model with aggregated parameters.
    """
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
        residual_units = 1
        if not (free_symbols & set(template.get_concept_names())):
            # We do subtitutions one by one so that we can keep track of which
            # parameters were used and adjust residual units accordingly
            for k, v in params_for_subs.items():
                starting_rate_law = residual_rate_law
                residual_rate_law = starting_rate_law.subs({k: v})
                # This means a substitution was made
                if starting_rate_law != residual_rate_law:
                    units = template_model.parameters[k].units.expression \
                        if template_model.parameters[k].units else 1
                    residual_units *= units
            if isinstance(residual_rate_law, (int, float)) or \
                    residual_rate_law.is_Number:
                pvalue = float(residual_rate_law)
                pname = f'mira_param_{idx}'
                # note that the distribution would be a product of the
                # original distributions if the original parameters
                # had them annotated
                template_model.parameters[pname] = \
                    Parameter(name=pname, value=pvalue, distribution=None,
                              units=Unit(expression=residual_units))
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
                                 GroupedControlledProduction,
                                 GroupedControlledDegradation)):
        return
    # Make a deepcopy up front so we don't change the original template
    template = deepcopy(template)
    # Start with the sympy.Expr representing the rate law
    rate_law = template.rate_law.args[0]
    new_templates = []
    # We go controller by controller and check if it's controlling the process
    # in a mass-action way.
    new_template_counter = 1
    for controller in deepcopy(template.controllers):
        # We use a trick here where we take the derivative of the rate law
        # with respect to the controller, and if it takes an expected form
        # we conclude that the controller is controlling the process in a
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
        elif isinstance(template, GroupedControlledDegradation) and \
                set(term_roles) == {'parameter', 'subject'}:
            new_template = ControlledDegradation(
                controller=deepcopy(controller),
                subject=deepcopy(template.subject),
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
        # Generate a new name for the template being created
        # but don't create a name if the original template didn't
        # have one either
        new_template.name = f"{template.name}_{new_template_counter}" if \
            template.name else None
        new_template_counter += 1
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


def get_term_roles(
    term,
    template: Template,
    parameters: Mapping[str, Parameter]
) -> Mapping[str, List[str]]:
    """Return terms in a rate law by role.

    Parameters
    ----------
    term :
        A sympy expression.
    template :
        A template.
    parameters :
        A dict of parameters in the template model, needed to interpret
        the semantics of rate laws.

    Returns
    -------
    :
        A dict of lists of symbols in the term by role.
    """
    term_roles = defaultdict(list)
    for symbol in term.free_symbols:
        if symbol.name in parameters:
            term_roles['parameter'].append(symbol.name)
        elif isinstance(template, (GroupedControlledConversion,
                                   GroupedControlledDegradation)) and \
                symbol.name == template.subject.name:
            term_roles['subject'].append(symbol.name)
        else:
            term_roles['other'].append(symbol.name)
    return dict(term_roles)


def counts_to_dimensionless(tm: TemplateModel,
                            counts_unit: str,
                            norm_factor: float) -> TemplateModel:
    """Convert all quantities using a given counts unit to dimensionless units.

    Parameters
    ----------
    tm :
        A template model.
    counts_unit :
        The unit of the counts.
    norm_factor :
        The normalization factor to convert counts to dimensionsionless.

    Returns
    -------
    :
        A template model with all entity concentrations converted to
        dimensionless units.
    """
    # Make a deepcopy up front so we don't change the original template model
    tm = deepcopy(tm)
    # Make a symbol of the counts unit for calculations
    counts_unit_symbol = sympy.Symbol(counts_unit)

    initials_normalized = set()
    # First we normalize concepts and their initials
    for template in tm.templates:
        # Since concepts can be distributed across templates, we have to go
        # template by template
        for concept in template.get_concepts():
            if concept.units:
                # We figure out what the exponent of the counts unit is
                # if it appears in the units of the concept
                (coeff, exponent) = \
                    concept.units.expression.args[0].as_coeff_exponent(counts_unit_symbol)
                # If the exponent is other than zero then normalization is needed
                if exponent:
                    concept.units.expression = \
                        SympyExprStr(concept.units.expression.args[0] /
                                     (counts_unit_symbol ** exponent))
                    # We not try to see if there is a corresponding initial condition
                    # for the concept and if so, we normalize it as well
                    if concept.name in tm.initials and concept.name not in initials_normalized:
                        init = tm.initials[concept.name]
                        if init.expression is not None:
                            init.expression = SympyExprStr(
                                init.expression.args[0] / (norm_factor ** exponent))
                            if init.concept.units:
                                init.concept.units.expression = \
                                    SympyExprStr(init.concept.units.expression.args[0] /
                                                 (counts_unit_symbol ** exponent))
                            initials_normalized.add(concept.name)
    # Now we do the same for parameters
    for p_name, p in tm.parameters.items():
        if p.units:
            (coeff, exponent) = \
                p.units.expression.args[0].as_coeff_exponent(counts_unit_symbol)
            if isinstance(exponent, sympy.core.numbers.One):
                exponent = 1
            if exponent:
                p.units.expression = \
                    SympyExprStr(p.units.expression.args[0] /
                                 (counts_unit_symbol ** exponent))
                p.value /= (norm_factor ** exponent)
                # Previously was sympy.Float object, cannot be serialized in
                # Pydantic2 type enforcement
                p.value = float(p.value)
    return tm


def deactivate_templates(
    template_model: TemplateModel,
    condition: Callable[[Template], bool]
):
    """Deactivate templates that satisfy a given condition.

    Parameters
    ----------
    template_model :
        A template model.
    condition :
        A function that takes a template and returns a boolean.
    """
    for template in template_model.templates:
        if condition(template):
            template.deactivate()


def add_observable_pattern(
    template_model: TemplateModel,
    name: str,
    identifiers: Mapping = None,
    context: Mapping = None,
):
    """Add an observable for a pattern of concepts.

    Parameters
    ----------
    template_model :
        A template model.
    name :
        The name of the observable.
    identifiers :
        Identifiers serving as a pattern for concepts to observe.
    context :
        Context serving as a pattern for concepts to observe.
    """
    observable_concepts = []
    identifiers = set(identifiers.items() if identifiers else {})
    contexts = set(context.items() if context else {})
    for key, concept in template_model.get_concepts_map().items():
        if (not identifiers) or identifiers.issubset(
                set(concept.identifiers.items())):
            if (not contexts) or contexts.issubset(
                    set(concept.context.items())):
                observable_concepts.append(concept)
    obs = get_observable_for_concepts(observable_concepts, name)
    template_model.observables[name] = obs


def get_observable_for_concepts(concepts: List[Concept], name: str):
    """Return an observable expressing a sum of a set of concepts.

    Parameters
    ----------
    concepts :
        A list of concepts.
    name :
        The name of the observable.

    Returns
    -------
    :
        An observable that sums the given concepts.
    """
    expr = None
    for concept in concepts:
        if expr is None:
            expr = sympy.Symbol(concept.name)
        else:
            expr += sympy.Symbol(concept.name)
    return Observable(name=name, expression=SympyExprStr(expr))