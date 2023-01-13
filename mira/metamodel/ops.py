"""Operations for template models."""

import itertools as itt
from typing import Iterable, List, Mapping, Optional, Set, Tuple, Type, Union

import sympy

from .templates import *

__all__ = [
    "stratify",
    "model_has_grounding",
    "find_models_with_grounding",
]


def stratify(
    template_model: TemplateModel,
    *,
    key: str,
    strata: Set[str],
    structure: Optional[Iterable[Tuple[str, str]]] = None,
    directed: bool = False,
    conversion_cls: Type[Template] = NaturalConversion,
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
        network structure.
    conversion_cls :
        The template class to be used for conversions between strata
        defined by the network structure. Defaults to :class:`NaturalConversion`

    Returns
    -------
    :
        A stratified template model
    """
    if structure is None:
        structure = list(itt.combinations(strata, 2))
        directed = False

    concepts = _get_concepts(template_model)

    templates = []
    # Generate a derived template for each strata
    for stratum, template in itt.product(strata, template_model.templates):
        templates.append(template.with_context(**{key: stratum}))
    # Generate a conversion between each concept of each strata based on the network structure
    for (source_stratum, target_stratum), concept in itt.product(structure, concepts):
        subject = concept.with_context(**{key: source_stratum})
        outcome = concept.with_context(**{key: target_stratum})
        # todo will need to generalize for different kwargs for different conversions
        templates.append(conversion_cls(subject=subject, outcome=outcome))
        if not directed:
            templates.append(conversion_cls(subject=outcome, outcome=subject))
    return TemplateModel(templates=templates)


def _get_concepts(template_model: TemplateModel):
    return list({concept.get_key(): concept for concept in _iter_concepts(template_model)}.values())


def _iter_concepts(template_model: TemplateModel):
    for template in template_model.templates:
        if isinstance(template, ControlledConversion):
            yield from (template.subject, template.outcome, template.controller)
        elif isinstance(template, NaturalConversion):
            yield from (template.subject, template.outcome)
        elif isinstance(template, GroupedControlledConversion):
            yield from template.controllers
            yield from (template.subject, template.outcome)
        elif isinstance(template, NaturalDegradation):
            yield template.subject
        elif isinstance(template, NaturalProduction):
            yield template.outcome
        else:
            raise TypeError(f"could not handle template: {template}")


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
    """Rewrite templates by simplifying rate laws.

    Parameters
    ----------
    template_model :
        A template model

    Returns
    -------
    :
        A template model with simplified rate laws (overwrites input,
        not a copy).
    """
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
    # We have a wrapper around the actual expression so we need to get
    # the single arg to get the actual sympy expression, then expand it
    # to turn e.g., x*y*(a+b) into x*y*a + x*y*b.
    rate_law = sympy.expand(template.rate_law.args[0])
    # We can now check whether the rate law is a single product term
    # or a sum of multiple terms
    if not rate_law.is_Add:
        return
    # Given that this is a sum of terms, we can go term-by-term to
    # check if each term can be broken out
    new_templates = []
    for term in rate_law.args:
        # For conversions, the pattern here is something like
        # parameter * controller * subject
        term_roles = get_term_roles(term, template, parameters)
        # If we found everything needed for an independent
        # conversion/production we are good to go in breaking this out
        new_template = None
        if isinstance(template, GroupedControlledConversion) and \
                set(term_roles) == {'parameter', 'controller', 'subject'}:
            new_template = ControlledConversion(
                controller=term_roles['controller'],
                subject=term_roles['subject'],
                outcome=template.outcome,
                rate_law=term
            )
        elif isinstance(template, GroupedControlledProduction) and \
                set(term_roles) == {'parameter', 'controller'}:
            new_template = ControlledProduction(
                controller=term_roles['controller'],
                outcome=template.outcome,
                rate_law=term
            )
        if new_template:
            new_templates.append(new_template)
            template.controllers.remove(term_roles['controller'])
            rate_law -= term

    if template.controllers:
        new_templates.append(template)
    return new_templates


def get_term_roles(term, template, parameters):
    """Return terms in a rate law by role."""
    if not term.is_Mul:
        return {}
    term_roles = {}
    controllers_by_name = {c.name: c for c in template.controllers}
    for arg in term.args:
        if arg.is_Number and arg == 1.0:
            continue
        elif arg.is_Symbol:
            if arg.name in parameters:
                term_roles['parameter'] = arg.name
            elif isinstance(template, GroupedControlledConversion) and \
                    arg.name == template.subject.name:
                term_roles['subject'] = template.subject
            elif arg.name in controllers_by_name:
                term_roles['controller'] = controllers_by_name[arg.name]
    return term_roles

