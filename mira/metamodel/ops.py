"""Operations for template models."""
import logging
from copy import deepcopy
from collections import defaultdict, Counter
import itertools as itt
from typing import Callable, Collection, Iterable, List, Mapping, Optional, \
    Tuple, Type, Union

import sympy

from .template_model import TemplateModel, Initial, Parameter
from .templates import *
from .units import Unit
from .utils import SympyExprStr

__all__ = [
    "stratify",
    "simplify_rate_laws",
    "aggregate_parameters",
    "get_term_roles",
    "counts_to_dimensionless",
    "deactivate_templates"
]


logger = logging.getLogger(__name__)


def stratify(
    template_model: TemplateModel,
    *,
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
    params_to_preserve:
        A list of parameters to preserve. If none given, will stratify all
        parameters.
    concepts_to_stratify :
        A list of concepts to stratify. If none given, will stratify all
        concepts.
    concepts_to_preserve:
        A list of concepts to preserve. If none given, will stratify all
        concepts.

    Returns
    -------
    :
        A stratified template model
    """
    strata = sorted(strata)

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

    templates = []
    params_count = Counter()

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

    keep_unstratified_parameters = set()
    for template in template_model.templates:
        # Generate a derived template for each strata
        for stratum in strata:
            new_template = None
            if set(template.get_concept_names()) - exclude_concepts:
                new_template = template.with_context(
                    do_rename=modify_names, exclude_concepts=exclude_concepts,
                    curie_to_name_map=strata_curie_to_name,
                    **{key: stratum},
                )
                rewrite_rate_law(template_model=template_model,
                                 old_template=template,
                                 new_template=new_template,
                                 params_count=params_count,
                                 params_to_stratify=params_to_stratify,
                                 params_to_preserve=params_to_preserve)
                # parameters = list(template_model.get_parameters_from_rate_law(template.rate_law))
                # if len(parameters) == 1:
                #     new_template.set_mass_action_rate_law(parameters[0])
                templates.append(new_template)

            # This means that the template had no concepts to stratify. This implies
            # that the template has no controllers that are stratified either
            # so we can skip the rest of this loop
            if not new_template:
                original_params = template.get_parameter_names()
                for param in original_params:
                    keep_unstratified_parameters.add(param)
                templates.append(deepcopy(template))
                continue

            # assume all controllers have to get stratified together
            # and mixing of strata doesn't occur during control
            controllers = template.get_controllers()
            if cartesian_control and controllers:
                remaining_strata = [s for s in strata if s != stratum]

                # use itt.product to generate all combinations of remaining
                # strata for remaining controllers. for example, if there
                # are two controllers A and B and stratification is into
                # old, middle, and young, then there will be the following 9:
                #    (A_old, B_old), (A_old, B_middle), (A_old, B_young),
                #    (A_middle, B_old), (A_middle, B_middle), (A_middle, B_young),
                #    (A_young, B_old), (A_young, B_middle), (A_young, B_young)
                c_strata_tuples = itt.product(remaining_strata, repeat=len(controllers))
                for c_strata_tuple in c_strata_tuples:
                    stratified_controllers = [
                        controller.with_context(do_rename=modify_names, **{key: c_stratum})
                        if controller.name not in exclude_concepts
                        else controller
                        for controller, c_stratum in zip(controllers, c_strata_tuple)
                    ]
                    if isinstance(template, (GroupedControlledConversion, GroupedControlledProduction)):
                        stratified_template = new_template.with_controllers(stratified_controllers)
                    elif isinstance(template, (ControlledConversion, ControlledProduction)):
                        assert len(stratified_controllers) == 1
                        stratified_template = new_template.with_controller(stratified_controllers[0])
                    else:
                        raise NotImplementedError
                    # the old template is used here on purpose for easier bookkeeping
                    rewrite_rate_law(template_model=template_model,
                                     old_template=template,
                                     new_template=stratified_template,
                                     params_count=params_count,
                                     params_to_stratify=params_to_stratify,
                                     params_to_preserve=params_to_preserve)
                    templates.append(stratified_template)

    parameters = {}
    for parameter_key, parameter in template_model.parameters.items():
        if parameter_key not in params_count:
            parameters[parameter_key] = parameter
            continue
        # We need to keep the original param if it has been broken
        # up but not in every instance. We then also
        # generate the counted parameter variants
        elif parameter_key in keep_unstratified_parameters:
            parameters[parameter_key] = parameter
        # note that `params_count[key]` will be 1 higher than the number of uses
        for i in range(params_count[parameter_key]):
            d = deepcopy(parameter)
            d.name = f"{parameter_key}_{i}"
            parameters[d.name] = d

    # Create new initial values for each of the strata
    # of the original compartments, copied from the initial
    # values of the original compartments
    initials = {}
    for initial_key, initial in template_model.initials.items():
        if initial.concept.name in exclude_concepts:
            initials[initial.concept.name] = deepcopy(initial)
            continue
        for stratum in strata:
            new_concept = initial.concept.with_context(
                do_rename=modify_names,
                curie_to_name_map=strata_curie_to_name,
                **{key: stratum},
            )
            initials[new_concept.name] = Initial(
                concept=new_concept, expression=SympyExprStr(initial.expression.args[0] / len(strata))
            )

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
    for (source_stratum, target_stratum), concept in itt.product(structure, concept_map.values()):
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
        template = conversion_cls(subject=subject, outcome=outcome)
        template.set_mass_action_rate_law(param_name)
        templates.append(template)
        if not directed:
            param_name = f"p_{target_stratum_name}_{source_stratum_name}"
            if param_name not in parameters:
                parameters[param_name] = Parameter(name=param_name, value=0.1)
            reverse_template = conversion_cls(subject=outcome, outcome=subject)
            reverse_template.set_mass_action_rate_law(param_name)
            templates.append(reverse_template)

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


def rewrite_rate_law(template_model: TemplateModel, old_template: Template,
                     new_template: Template, params_count,
                     params_to_stratify=None, params_to_preserve=None):
    # Rewrite the rate law by substituting new symbols corresponding
    # to the stratified controllers in for the originals
    rate_law = old_template.rate_law
    if not rate_law:
        return

    # Step 1. Identify the mass action symbol and rename it with a
    parameters = list(template_model.get_parameters_from_rate_law(rate_law))
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
            rate_law = rate_law.subs(
                parameter,
                sympy.Symbol(f"{parameter}_{params_count[parameter]}")
            )
            params_count[parameter] += 1  # increment this each time to keep unique

    # Step 2. Rename symbols corresponding to compartments based on the new concepts
    for old_controller, new_controller in zip(
        old_template.get_controllers(), new_template.get_controllers(),
    ):
        rate_law = rate_law.subs(
            sympy.Symbol(old_controller.name),
            sympy.Symbol(new_controller.name),
        )

    # Step 3. Rename subject and object
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

    new_template.rate_law = rate_law


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


def aggregate_parameters(template_model, exclude=None):
    """Return a template model after aggregating parameters for mass-action
    rate laws.

    Parameters
    ----------
    template_model :
        A template model whose rate laws will be aggregated.
    exclude :
        A list of parameters to exclude from aggregation.

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


def counts_to_dimensionless(tm: TemplateModel,
                            counts_unit: str,
                            norm_factor: float):
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

    return tm


def deactivate_templates(template_model: TemplateModel,
                         condition: Callable[[Template], bool]):
    """Deactivate templates that satisfy a given condition."""
    for template in template_model.templates:
        if condition(template):
            template.deactivate()
