"""Operations for template models."""

import itertools as itt
from typing import Iterable, Optional, Set, Tuple, Type

from ..metamodel import ControlledConversion, NaturalConversion, Template
from . import TemplateModel

__all__ = [
    "stratify",
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

    :param template_model: A template model
    :param key: The (singular) name of the stratification, e.g., ``"city"``
    :param strata: A list of the values for stratitication, e.g., ``["boston", "nyc"]``
    :param structure: An iterable of pairs corresponding to a directed network structure
        where each of the pairs has two strata. If none given, will assume a complete
        network structure.
    :param conversion_cls: The template class to be used for conversions between strata
        defined by the network structure. Defaults to :class:`NaturalConversion`
    :returns: A stratified template model
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
        else:
            raise TypeError(f"could not handle template: {template}")
