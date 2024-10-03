"""
Data models for metamodel templates.

Regenerate the JSON schema by running ``python -m mira.metamodel.schema``.
"""
import copy

from pydantic import ConfigDict
from typing import Literal

__all__ = [
    "Concept",
    "Template",
    "Provenance",
    "ControlledConversion",
    "ControlledProduction",
    "ControlledDegradation",
    "NaturalConversion",
    "NaturalProduction",
    "NaturalDegradation",
    "GroupedControlledConversion",
    "GroupedControlledProduction",
    "GroupedControlledDegradation",
    "MultiConversion",
    "NaturalReplication",
    "ControlledReplication",
    "ReversibleFlux",
    "StaticConcept",
    "SpecifiedTemplate",
    "templates_equal",
    "context_refinement",
    "match_concepts",
    "is_production",
    "is_degradation",
    "is_conversion",
    "is_replication",
    "is_reversible",
    "has_subject",
    "has_outcome",
    "has_controller",
    "num_controllers",
    "get_binding_templates",
    "conversion_to_deg_prod",
]

import logging
import sys
from collections import ChainMap
from copy import deepcopy
from itertools import product
from typing import (
    Callable,
    ClassVar,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Set,
    Tuple,
    Union,
)

import networkx as nx
import pydantic
import sympy
from pydantic import BaseModel, Field, field_serializer

try:
    from typing import Annotated  # py39+
except ImportError:
    from typing_extensions import Annotated

from .units import Unit, UNIT_SYMBOLS
from .utils import safe_parse_expr, SympyExprStr


IS_EQUAL = "is_equal"
REFINEMENT_OF = "refinement_of"
CONTROLLERS = "controllers"
CONTROLLER = "controller"
OUTCOME = "outcome"
SUBJECT = "subject"

logger = logging.getLogger(__name__)


class Config(BaseModel):
    """Config determining how keys are generated"""

    prefix_priority: List[str] = Field(
        default_factory=list,
        description="The priority list of prefixes for identifiers."
    )
    prefix_exclusions: List[str] = Field(
        default_factory=list,
        description="The list of prefixes to exclude."
    )


DEFAULT_CONFIG = Config(
    prefix_priority=[
        "ido",
    ],
    prefix_exclusions=[
        "biomodels.species"
    ],
)


class Concept(BaseModel):
    """A concept is specified by its identifier(s), name, and - optionally -
    its context.
    """

    name: str = Field(..., description="The name of the concept.")
    display_name: Optional[str]= \
        Field(None, description="An optional display name for the concept. "
                                "If not provided, the name can be used for "
                                "display purposes.")
    description: Optional[str] = \
        Field(None, description="An optional description of the concept.")
    identifiers: Mapping[str, str] = Field(
        default_factory=dict, description="A mapping of namespaces to identifiers."
    )
    context: Mapping[str, Union[str,int]] = Field(
        default_factory=dict, description="A mapping of context keys to values."
    )
    units: Optional[Unit] = Field(
        None, description="The units of the concept."
    )
    _base_name: str = pydantic.PrivateAttr(None)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def with_context(self, do_rename=False, curie_to_name_map=None,
                     inplace=False, **context) -> "Concept":
        """Return this concept with extra context.

        Parameters
        ----------
        do_rename :
            If true, will modify the name of the node based on the context
            introduced
        curie_to_name_map :
            Use to set a name different from the context values provided in
            the `**context` kwarg when do_rename=True. Useful if
            the context values are e.g. curies or longer names that should
            be shortened, like {"New York City": "nyc"}. If not provided (
            default behavior), the context values will be used as names.
        inplace : bool
            If True, modify the concept in place. Default: False.
        **context :
            The context to add to the concept.

        Returns
        -------
        :
            A new concept containing the given context.
        """
        if do_rename:
            if self._base_name is None:
                self._base_name = self.name
            name_list = [self._base_name]
            for _, context_value in sorted(context.items()):
                entity_name = curie_to_name_map.get(
                    context_value, context_value
                ) if curie_to_name_map else context_value
                name_list.append(str(entity_name.replace(':', '_')))
            name = '_'.join(name_list)
        else:
            name = self.name
        full_context = dict(ChainMap(context, self.context))
        if inplace:
            self.name = name
            self.context = full_context
            concept = self
        else:
            concept = Concept(
                name=name,
                display_name=self.display_name,
                identifiers=self.identifiers,
                context=full_context,
                units=self.units,
            )
            concept._base_name = self._base_name
        return concept

    def get_curie(self, config: Optional[Config] = None) -> Tuple[str, str]:
        """Get the priority prefix/identifier pair for this concept.

        Parameters
        ----------
        config :
            Configuration defining priority and exclusion for identifiers.

        Returns
        -------
        :
            A tuple of the priority prefix and identifier for this concept.
        """
        if config is None:
            config = DEFAULT_CONFIG
        identifiers = {k: v for k, v in self.identifiers.items()
                       if k not in config.prefix_exclusions}

        # If ungrounded, return empty prefix and name
        if not identifiers:
            return "", self.name

        # If there are identifiers get one from the priority list
        for prefix in config.prefix_priority:
            identifier = identifiers.get(prefix)
            if identifier:
                return prefix, identifier

        # Fallback to the identifiers outside the priority list
        return sorted(identifiers.items())[0]

    def get_curie_str(self, config: Optional[Config] = None) -> str:
        """Get the priority prefix/identifier as a CURIE string.

        Parameters
        ----------
        config :
            Configuration defining priority and exclusion for identifiers.

        Returns
        -------
        :
            A CURIE string for this concept.
        """
        return ":".join(self.get_curie(config=config))

    def get_included_identifiers(self, config: Optional[Config] = None) -> Dict[str, str]:
        """Get the identifiers for this concept that are not excluded.

        Parameters
        ----------
        config :
            Configuration defining priority and exclusion for identifiers.

        Returns
        -------
        :
            A dict of identifiers for this concept that are not excluded as
            defined by the config.
        """
        config = DEFAULT_CONFIG if config is None else config
        return {k: v for k, v in self.identifiers.items() if k not in config.prefix_exclusions}

    def get_key(self, config: Optional[Config] = None):
        """Get the key for this concept.

        Parameters
        ----------
        config :
            Configuration defining priority and exclusion for identifiers.

        Returns
        -------
        :
            A tuple of the priority prefix and identifier together with the
            sorted context of this concept.
        """
        return (
            self.get_curie(config=config),
            tuple(sorted(self.context.items())),
        )

    def is_equal_to(self, other: "Concept", with_context: bool = False,
                    config: Config = None) -> bool:
        """Test for equality between concepts

        Parameters
        ----------
        other :
            Other Concept to test equality with
        with_context :
            If True, do not consider the two Concepts equal unless they also
            have exactly the same context. If there is no context,
            ``with_context`` has no effect.
        config :
            Configuration defining priority and exclusion for identifiers.

        Returns
        -------
        :
            True if ``other`` is the same Concept as this one
        """
        if not isinstance(other, Concept):
            return False

        # With context
        if with_context:
            # Check that the same keys appear in both
            if set(self.context.keys()) != set(other.context.keys()):
                return False

            # Check that the values are the same
            for k1, v1 in self.context.items():
                if v1 != other.context[k1]:
                    return False

        # Check that they are grounded to the same identifier
        return self.get_curie(config=config) == other.get_curie(config=config)

    def refinement_of(
        self,
        other: "Concept",
        refinement_func: Callable[[str, str], bool],
        with_context: bool = False,
        config: Config = None,
    ) -> bool:
        """Check if this Concept is a more detailed version of another

        Parameters
        ----------
        other :
            The other Concept to compare with. Assumed to be less detailed.
        with_context :
            If True, also consider the context of the Concepts for the
            refinement.
        refinement_func :
            A function that given a source/more detailed entity and a
            target/less detailed entity checks if they are in a child-parent and
            returns a boolean.
        config :
            Configuration defining priority and exclusion for identifiers.

        Returns
        -------
        :
            True if this Concept is a refinement of another Concept
        """
        if not isinstance(other, Concept):
            return False

        # If they have equivalent identity, we allow as possible refinement
        if self.is_equal_to(other, with_context=False):
            ontological_refinement = True
        # Otherwise we assume refinement is not possible, except if both
        # are grounded, and there is a refinement relationship per
        # a refinement function between them
        else:
            ontological_refinement = False
            # Check if this concept is a child term to other?
            this_prefix, this_id = self.get_curie(config=config)
            other_prefix, other_id = other.get_curie(config=config)
            if this_prefix and other_prefix:
                # Check if other is a parent of this concept
                this_curie = f"{this_prefix}:{this_id}"
                other_curie = f"{other_prefix}:{other_id}"
                ontological_refinement = refinement_func(this_curie, other_curie)

        contextual_refinement = True
        if with_context:
            contextual_refinement = \
                context_refinement(self.context, other.context)

        return ontological_refinement and contextual_refinement

    @classmethod
    def from_json(cls, data) -> "Concept":
        """Create a Concept from its JSON representation.

        Parameters
        ----------
        data :
            The JSON representation of the Concept.

        Returns
        -------
        :
            The Concept object.
        """
        # Handle Units
        if isinstance(data, Concept):
            return data
        elif data.get('units'):
            # Copy so we don't update the input
            data = copy.deepcopy(data)
            data['units'] = Unit.from_json(data['units'])

        return cls(**data)


class Template(BaseModel):
    """The Template is a parent class for model processes"""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    rate_law: Optional[SympyExprStr] = Field(
        default=None, description="The rate law for the template."
    )
    name: Optional[str] = Field(
        default=None, description="The name of the template."
    )
    display_name: Optional[str] = Field(
        default=None, description="The display name of the template."
    )

    @classmethod
    def from_json(cls, data, rate_symbols=None) -> "Template":
        """Create a Template from a JSON object

        Parameters
        ----------
        data :
            The JSON object to create the Template from
        rate_symbols :
            A mapping of symbols to use for the rate law. If not provided,
            the rate law will be parsed without any symbols.

        Returns
        -------
        :
            A Template object
        """
        # Make a copy to make sure we don't update the input
        data = copy.deepcopy(data)
        # We make sure to use data such that it's not modified in place,
        # e.g., we don't use pop or overwrite items, otherwise this function
        # would have unintended side effects.

        # First, we need to figure out the template class based on the type
        # entry in the data
        stmt_cls = getattr(sys.modules[__name__], data['type'])

        # In order to correctly parse the rate, if any, we need to have access
        # to symbols representing parameters, these are passed in from
        # outside, typically the template model level.
        rate_str = data.get('rate_law')
        if rate_str:
            rate = safe_parse_expr(rate_str, local_dict=rate_symbols)
        else:
            rate = None

        # Handle concepts
        for concept_key in stmt_cls.concept_keys:
            if concept_key in data:
                concept_data = data[concept_key]
                # Handle lists of concepts for e.g. controllers in
                # GroupedControlledConversion
                if isinstance(concept_data, list):
                    data[concept_key] = [Concept.from_json(c) for c in concept_data]
                else:
                    data[concept_key] = Concept.from_json(data[concept_key])

        return stmt_cls(**{k: v for k, v in data.items()
                           if k not in {'rate_law', 'type'}},
                        rate_law=rate)

    @field_serializer('rate_law', when_used="unless-none")
    def serialize_expression(self, rate_law):
        return str(rate_law)

    def is_equal_to(self, other: "Template", with_context: bool = False,
                    config: Config = None) -> bool:
        """Check if this template is equal to another template

        Parameters
        ----------
        other :
            The other template to check for equality with this one with
        with_context :
            If True, the contexts are taken into account when checking for
            equality. Default: False.
        config :
            Configuration defining priority and exclusion for identifiers.

        Returns
        -------
        :
            True if the other Template is equal to this Template
        """
        if not isinstance(other, Template):
            return False
        return templates_equal(self, other, with_context=with_context,
                               config=config)

    def refinement_of(
        self,
        other: "Template",
        refinement_func: Callable[[str, str], bool],
        with_context: bool = False,
        config: Config = None,
    ) -> bool:
        """Check if this template is a more detailed version of another

        Parameters
        ----------
        other :
            The other template to compare with. Is assumed to be less
            detailed than this template.
        with_context :
            If True, also consider the context of Templates' Concepts for the
            refinement.
        refinement_func :
            A function that given a source/more detailed entity and a
            target/less detailed entity checks if they are in a child-parent
            relationship and returns a boolean.

        Returns
        -------
        :
            True if this Template is a refinement of the other Template.
        """
        if not isinstance(other, Template):
            return False

        compatibilities = {
            ('ControlledConversion', 'NaturalConversion'),
            ('GroupedControlledConversion', 'NaturalConversion'),
            ('GroupedControlledConversion', 'ControlledConversion')
        }

        if self.type != other.type and \
                (self.type, other.type) not in compatibilities:
            return False

        other_by_role = other.get_concepts_by_role()
        for role, value in self.get_concepts_by_role().items():
            # This is a special case to handle the list vs single controller
            # with distinct role names
            if role == 'controllers':
                if 'controllers' in other_by_role:
                    other_value = other_by_role['controllers']
                elif 'controller'in other_by_role:
                    other_value = [other_by_role['controller']]
                else:
                    other_value = None
            else:
                other_value = other_by_role.get(role)
            # This case handles less detailed other classes where a given
            # role might be missing
            if other_value is None:
                continue
            # When we are comparing concepts
            if isinstance(value, Concept):
                if not value.refinement_of(other_value,
                                           refinement_func=refinement_func,
                                           with_context=with_context,
                                           config=config):
                    return False
            # When we are comparing lists of concepts
            elif isinstance(value, list):
                if not match_concepts(value, other_value,
                                      with_context=with_context,
                                      config=config,
                                      refinement_func=refinement_func):
                    return False
        return True

    def with_context(
        self,
        do_rename=False,
        exclude_concepts=None,
        curie_to_name_map=None,
        **context
    ):
        """Return a copy of this template with context added

        Parameters
        ----------
        do_rename :
            If True, rename the names of the concepts
        exclude_concepts :
            A set of concept names to keep unchanged.
        curie_to_name_map :
            A mapping of context values to names. Useful if the context values
            are e.g. curies. Will only be used if ``do_rename`` is True.

        Returns
        -------
        :
            A copy of this template with context added
        """
        raise NotImplementedError("This method can only be called on subclasses")

    def get_concepts(self) -> List[Union[Concept, List[Concept]]]:
        """Return the concepts in this template.

        Returns
        -------
        :
            A list of concepts in this template.
        """
        if not hasattr(self, "concept_keys"):
            raise NotImplementedError(
                "This method can only be called on subclasses of Template"
            )
        return [getattr(self, k) for k in self.concept_keys]

    def get_concepts_flat(self, exclude_controllers=False,
                          refresh=False) -> List[Concept]:
        """Return the concepts in this template as a flat list.

        Attributes where a list of concepts is expected are flattened.
        """
        concepts_flat = []
        for role, value in self.get_concepts_by_role().items():
            if role in {'controllers', 'controller'} and exclude_controllers:
                continue
            if isinstance(value, list):
                if refresh:
                    setattr(self, role, [deepcopy(v) for v in value])
                concepts_flat.extend(getattr(self, role))
            else:
                if refresh:
                    setattr(self, role, deepcopy(value))
                concepts_flat.append(getattr(self, role))
        return concepts_flat

    def get_concepts_by_role(self) -> Dict[str, Concept]:
        """Return the concepts in this template as a dict keyed by role.

        Returns
        -------
        :
            A dict of concepts in this template keyed by role.
        """
        return {
            k: getattr(self, k) for k in self.concept_keys
        }

    def get_concept_names(self) -> Set[str]:
        """Return the concept names in this template.

        Returns
        -------
        :
            The set of concept names in this template.
        """
        return {c.name for c in self.get_concepts()}

    def get_interactors(self) -> List[Concept]:
        """Return the interactors in this template.

        Returns
        -------
        :
            A list of interactors in this template.
        """
        concepts_by_role = self.get_concepts_by_role()
        if 'controller' in concepts_by_role:
            controllers = [concepts_by_role['controller']]
        elif 'controllers' in concepts_by_role:
            controllers = concepts_by_role['controllers']
        else:
            controllers = []
        subject = concepts_by_role.get('subject')
        interactors = controllers + ([subject] if subject else [])
        return interactors

    def get_controllers(self) -> List[Concept]:
        """Return the controllers in this template.

        Returns
        -------
        :
            A list of controllers in this template.
        """
        concepts_by_role = self.get_concepts_by_role()
        if 'controller' in concepts_by_role:
            controllers = [concepts_by_role['controller']]
        elif 'controllers' in concepts_by_role:
            controllers = concepts_by_role['controllers']
        else:
            controllers = []
        return controllers

    def get_interactor_rate_law(self, independent=False) -> sympy.Expr:
        """Return the rate law for the interactors in this template.

        This is the part of the rate law that is the product of the interactors
        but does not include any parameters.

        Parameters
        ----------
        independent :
            If True, the controllers will assume independent action.

        Returns
        -------
        :
            The rate law for the interactors in this template.
        """
        rate_law = 1
        if not independent:
            for interactor in self.get_interactors():
                rate_law *= sympy.Symbol(interactor.name)
        else:
            concepts_by_role = self.get_concepts_by_role()
            subject = concepts_by_role.get('subject')
            controllers = self.get_controllers()
            rate_law *= sympy.Symbol(subject.name)
            controller_terms = 0
            for controller in controllers:
                controller_terms += sympy.Symbol(controller.name)
            rate_law *= controller_terms
        return rate_law

    def get_mass_action_rate_law(self, parameter: str, independent=False) -> sympy.Expr:
        """Return the mass action rate law for this template.

        Parameters
        ----------
        parameter :
            The parameter to use for the mass-action rate law.
        independent :
            If True, the controllers will assume independent action.

        Returns
        -------
        :
            The mass action rate law for this template.
        """
        param_term = sympy.Symbol(parameter) if isinstance(parameter, str) \
            else parameter
        rate_law = param_term * \
            self.get_interactor_rate_law(independent=independent)
        return rate_law

    def get_independent_mass_action_rate_law(self, parameter: str) -> sympy.Expr:
        """Return the mass action rate law for this template with independent
        action.

        Parameters
        ----------
        parameter :
            The parameter to use for the mass-action rate.

        Returns
        -------
        :
            The mass action rate law for this template with independent action.
        """
        rate_law = sympy.Symbol(parameter) * \
            self.get_interactor_rate_law(independent=True)
        return rate_law

    def set_mass_action_rate_law(self, parameter, independent=False):
        """Set the rate law of this template to a mass action rate law.

        Parameters
        ----------
        parameter :
            The parameter to use for the mass-action rate.
        independent :
            If True, the controllers will assume independent action.
        """
        self.rate_law = SympyExprStr(
            self.get_mass_action_rate_law(parameter, independent=independent))

    def with_mass_action_rate_law(self, parameter, independent=False) -> "Template":
        """Return a copy of this template with a mass action rate law.

        Parameters
        ----------
        parameter :
            The parameter to use for the mass-action rate.
        independent :
            If True, the controllers will assume independent action.

        Returns
        -------
        :
            A copy of this template with the mass action rate law.
        """
        template = self.model_copy(deep=True)
        template.set_mass_action_rate_law(parameter, independent=independent)
        return template

    def set_rate_law(self, rate_law: Union[str, sympy.Expr, SympyExprStr],
                     local_dict=None):
        """Set the rate law of this template to the given rate law."""
        if isinstance(rate_law, SympyExprStr):
            self.rate_law = rate_law
        elif isinstance(rate_law, sympy.Expr):
            self.rate_law = SympyExprStr(rate_law)
        elif isinstance(rate_law, str):
            try:
                rate = SympyExprStr(safe_parse_expr(rate_law,
                                                    local_dict=local_dict))
            except Exception as e:
                logger.warning(f"Could not parse rate law into "
                               f"symbolic expression: {rate_law}. "
                               f"Not setting rate law.")
                return
            self.rate_law = rate

    def with_rate_law(self, rate_law: Union[str, sympy.Expr, SympyExprStr],
                      local_dict=None) -> "Template":
        template = self.model_copy(deep=True)
        template.set_rate_law(rate_law, local_dict=local_dict)
        return template

    def get_parameter_names(self) -> Set[str]:
        """Get the set of parameter names.

        Returns
        -------
        :
            The set of parameter names.
        """
        if not self.rate_law:
            return set()
        return (
            {s.name for s in self.rate_law.args[0].free_symbols}
            - self.get_concept_names()
        )

    def update_parameter_name(self, old_name: str, new_name: str):
        """Update the name of a parameter in the rate law.

        Parameters
        ----------
        old_name :
            The old name of the parameter.
        new_name :
            The new name of the parameter.
        """
        if self.rate_law:
            self.rate_law = self.rate_law.subs(sympy.Symbol(old_name),
                                               sympy.Symbol(new_name))

    def get_mass_action_symbol(self) -> Optional[sympy.Symbol]:
        """Get the symbol for the parameter associated with this template's rate law,
        assuming it's mass action.

        Returns
        -------
        :
            The symbol for the parameter associated with this template's rate law,
            assuming it's mass action. Returns None if the rate law is not
            mass action or if there is no rate law.
        """
        if not self.rate_law:
            return None
        results = sorted(self.get_parameter_names())
        if not results:
            return None
        if len(results) == 1:
            return sympy.Symbol(results[0])
        raise ValueError("recovered multiple parameters - not mass action")

    def substitute_parameter(self, name: str, value):
        """Substitute a parameter in this template's rate law.

        Parameters
        ----------
        name :
            The name of the parameter to substitute.
        value :
            The value to substitute.
        """
        if not self.rate_law:
            return
        self.rate_law = SympyExprStr(
            self.rate_law.args[0].subs(sympy.Symbol(name), value))

    def deactivate(self):
        """Deactivate this template by setting its rate law to zero."""
        if self.rate_law:
            self.rate_law = SympyExprStr(self.rate_law.args[0] * 0)

    def get_key(self, config: Optional[Config] = None) -> Tuple:
        """Get the key for this template.

        Parameters
        ----------
        config :
            Configuration defining priority and exclusion for identifiers.

        Returns
        -------
        :
            A tuple of the type and concepts in this template.
        """
        raise NotImplementedError("This method can only be called on subclasses")


class Provenance(BaseModel):
    pass


class ControlledConversion(Template):
    """Specifies a process of controlled conversion from subject to outcome,
    controlled by the controller."""

    type: Literal["ControlledConversion"] = "ControlledConversion"
    controller: Concept = Field(..., description="The controller of the conversion.")
    subject: Concept = Field(..., description="The subject of the conversion.")
    outcome: Concept = Field(..., description="The outcome of the conversion.")
    provenance: List[Provenance] = Field(default_factory=list, description="The provenance of the conversion.")

    concept_keys: ClassVar[List[str]] = ["controller", "subject", "outcome"]

    def with_context(
        self,
        do_rename=False,
        exclude_concepts=None,
        curie_to_name_map=None,
        **context
    ) -> "ControlledConversion":
        exclude_concepts = exclude_concepts or set()
        return self.__class__(
            type=self.type,
            subject=self.subject if self.subject.name in exclude_concepts else
                     self.subject.with_context(do_rename=do_rename,
                                               curie_to_name_map=curie_to_name_map,
                                               **context),
            outcome=self.outcome if self.outcome.name in exclude_concepts else
                     self.outcome.with_context(do_rename=do_rename,
                                               curie_to_name_map=curie_to_name_map,
                                               **context),
            controller=self.controller if self.controller.name in exclude_concepts else
                        self.controller.with_context(do_rename=do_rename,
                                                     curie_to_name_map=curie_to_name_map,
                                                     **context),
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def add_controller(self, controller: Concept) -> "GroupedControlledConversion":
        """Add a controller to this template.

        Parameters
        ----------
        controller :
            The controller to add.

        Returns
        -------
        :
            A new template with the additional controller.
        """
        return GroupedControlledConversion(
            subject=self.subject,
            outcome=self.outcome,
            provenance=self.provenance,
            controllers=[self.controller, controller]
        )

    def with_controller(self, controller) -> "ControlledConversion":
        """Return a copy of this template with the given controller.

        Parameters
        ----------
        controller :
            The controller to use for the new template.

        Returns
        -------
        :
            A copy of this template with the given controller.
        """
        return self.__class__(
            type=self.type,
            controller=controller,
            subject=self.subject,
            outcome=self.outcome,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.subject.get_key(config=config),
            self.controller.get_key(config=config),
            self.outcome.get_key(config=config),
        )


class GroupedControlledConversion(Template):
    type: Literal["GroupedControlledConversion"] = "GroupedControlledConversion"
    controllers: List[Concept] = Field(..., description="The controllers of the conversion.")
    subject: Concept = Field(..., description="The subject of the conversion.")
    outcome: Concept = Field(..., description="The outcome of the conversion.")
    provenance: List[Provenance] = Field(default_factory=list, description="The provenance of the conversion.")

    concept_keys: ClassVar[List[str]] = ["controllers", "subject", "outcome"]

    def with_context(
        self,
        do_rename=False,
        exclude_concepts=None,
        curie_to_name_map=None,
        **context
    ) -> "GroupedControlledConversion":
        exclude_concepts = exclude_concepts or set()

        return self.__class__(
            type=self.type,
            controllers=[c.with_context(do_rename=do_rename,
                                        curie_to_name_map=curie_to_name_map,
                                        **context)
                         if c.name not in exclude_concepts else c
                         for c in self.controllers],
            subject=self.subject if self.subject.name in exclude_concepts else
                        self.subject.with_context(
                            do_rename=do_rename, curie_to_name_map=curie_to_name_map, **context
                        ),
            outcome=self.outcome if self.outcome.name in exclude_concepts else
                        self.outcome.with_context(
                            do_rename=do_rename, curie_to_name_map=curie_to_name_map, **context
                        ),
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def with_controllers(self, controllers) -> "GroupedControlledConversion":
        """Return a copy of this template with the given controllers.

        Parameters
        ----------
        controllers :
            The controllers to use for the new template.

        Returns
        -------
        :
            A copy of this template with the given controllers.
        """
        if len(self.controllers) != len(controllers):
            raise ValueError(
                f"Must replace all controllers. Expecting "
                f"{len(self.controllers)} controllers, got {len(controllers)}"
            )
        return self.__class__(
            type=self.type,
            controllers=controllers,
            subject=self.subject,
            outcome=self.outcome,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            *tuple(
                c.get_key(config=config)
                for c in sorted(self.controllers, key=lambda c: c.get_key(config=config))
            ),
            self.subject.get_key(config=config),
            self.outcome.get_key(config=config),
        )

    def get_concepts(self):
        return self.controllers + [self.subject, self.outcome]

    def add_controller(self, controller: Concept) -> "GroupedControlledConversion":
        """Add an additional controller."""
        return GroupedControlledConversion(
            subject=self.subject,
            outcome=self.outcome,
            provenance=self.provenance,
            controllers=[*self.controllers, controller]
        )


class GroupedControlledProduction(Template):
    """Specifies a process of production controlled by several controllers"""

    type: Literal["GroupedControlledProduction"] = "GroupedControlledProduction"
    controllers: List[Concept] = Field(..., description="The controllers of the production.")
    outcome: Concept = Field(..., description="The outcome of the production.")
    provenance: List[Provenance] = Field(default_factory=list, description="The provenance of the production.")

    concept_keys: ClassVar[List[str]] = ["controllers", "outcome"]

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            *tuple(
                c.get_key(config=config)
                for c in sorted(self.controllers, key=lambda c: c.get_key(config=config))
            ),
            self.outcome.get_key(config=config),
        )

    def get_concepts(self):
        return self.controllers + [self.outcome]

    def add_controller(self, controller: Concept) -> "GroupedControlledProduction":
        """Add a controller to this template.

        Parameters
        ----------
        controller :
            The controller to add.

        Returns
        -------
        :
            A new template with the additional controller.
        """
        return GroupedControlledProduction(
            outcome=self.outcome,
            provenance=self.provenance,
            controllers=[*self.controllers, controller]
        )

    def with_controllers(self, controllers) -> "GroupedControlledProduction":
        """Return a copy of this template with the given controllers.

        Parameters
        ----------
        controllers :
            The controllers to use for the new template.

        Returns
        -------
        :
            A copy of this template with the given controllers replacing the
            existing controllers.
        """
        return self.__class__(
            type=self.type,
            controllers=controllers,
            outcome=self.outcome,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def with_context(
        self,
        do_rename=False,
        exclude_concepts=None,
        curie_to_name_map=None,
        **context
    ) -> "GroupedControlledProduction":
        exclude_concepts = exclude_concepts or set()
        return self.__class__(
            type=self.type,
            controllers=[c.with_context(do_rename, curie_to_name_map=curie_to_name_map, **context)
                         if c.name not in exclude_concepts else c
                         for c in self.controllers],
            outcome=self.outcome.with_context(
                do_rename, curie_to_name_map=curie_to_name_map, **context
            )
                if self.outcome.name not in exclude_concepts else self.outcome,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )


class ControlledProduction(Template):
    """Specifies a process of production controlled by one controller"""

    type: Literal["ControlledProduction"] = "ControlledProduction"
    controller: Concept = Field(
        ..., description="The controller of the production."
    )
    outcome: Concept = Field(
        ..., description="The outcome of the production."
    )
    provenance: List[Provenance] = Field(
        default_factory=list, description="Provenance of the template"
    )

    concept_keys: ClassVar[List[str]] = ["controller", "outcome"]

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.controller.get_key(config=config),
            self.outcome.get_key(config=config),
        )

    def add_controller(self, controller: Concept) -> "GroupedControlledProduction":
        """Add a controller to this template.

        Parameters
        ----------
        controller :
            The controller to add.

        Returns
        -------
        :
            A GroupedControlledProduction template with the additional
            controller.
        """
        return GroupedControlledProduction(
            outcome=self.outcome,
            provenance=self.provenance,
            controllers=[self.controller, controller]
        )

    def with_controller(self, controller) -> "ControlledProduction":
        """Return a copy of this template with the given controller.

        Parameters
        ----------
        controller :
            The controller to use for the new template.

        Returns
        -------
        :
            A copy of this template with the given controller replacing the
            existing controller.
        """
        return self.__class__(
            type=self.type,
            controller=controller,
            outcome=self.outcome,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def with_context(
        self,
        do_rename=False,
        exclude_concepts=None,
        curie_to_name_map=None,
        **context
    ) -> "ControlledProduction":
        exclude_concepts = exclude_concepts or set()
        return self.__class__(
            type=self.type,
            outcome=self.outcome.with_context(
                do_rename=do_rename, curie_to_name_map=curie_to_name_map, **context
            ) if self.outcome.name not in exclude_concepts else self.outcome,
            controller=self.controller.with_context(
                do_rename=do_rename, curie_to_name_map=curie_to_name_map, **context
            ) if self.controller.name not in exclude_concepts else self.controller,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )


class NaturalConversion(Template):
    """Specifies a process of natural conversion from subject to outcome"""

    type: Literal["NaturalConversion"] = "NaturalConversion"
    subject: Concept = Field(..., description="The subject of the conversion.")
    outcome: Concept = Field(..., description="The outcome of the conversion.")
    provenance: List[Provenance] = Field(default_factory=list, description="The provenance of the conversion.")

    concept_keys: ClassVar[List[str]] = ["subject", "outcome"]

    def with_context(
        self,
        do_rename=False,
        exclude_concepts=None,
        curie_to_name_map=None,
        **context
    ) -> "NaturalConversion":
        exclude_concepts = exclude_concepts or set()
        return self.__class__(
            type=self.type,
            subject=self.subject.with_context(
                do_rename=do_rename, curie_to_name_map=curie_to_name_map, **context
            ) if self.subject.name not in exclude_concepts else self.subject,
            outcome=self.outcome.with_context(
                do_rename=do_rename, curie_to_name_map=curie_to_name_map, **context
            ) if self.outcome.name not in exclude_concepts else self.outcome,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.subject.get_key(config=config),
            self.outcome.get_key(config=config),
        )


class MultiConversion(Template):
    """Specifies a conversion process of multiple subjects and outcomes."""

    type: Literal["MultiConversion"] = "MultiConversion"
    subjects: List[Concept] = Field(..., description="The subjects of the conversion.")
    outcomes: List[Concept] = Field(..., description="The outcomes of the conversion.")
    provenance: List[Provenance] = Field(default_factory=list, description="The provenance of the conversion.")

    concept_keys: ClassVar[List[str]] = ["subjects", "outcomes"]

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            *tuple(
                c.get_key(config=config)
                for c in sorted(self.subjects, key=lambda c: c.get_key(config=config))
            ),
            *tuple(
                c.get_key(config=config)
                for c in sorted(self.outcomes, key=lambda c: c.get_key(config=config))
            ),
        )

    def get_concepts(self):
        return self.subjects + self.outcomes

    def with_context(
            self,
            do_rename=False,
            exclude_concepts=None,
            curie_to_name_map=None,
            **context
    ) -> "MultiConversion":
        exclude_concepts = exclude_concepts or set()
        return self.__class__(
            type=self.type,
            subjects=[c.with_context(do_rename, curie_to_name_map=curie_to_name_map, **context)
                      if c.name not in exclude_concepts else c
                      for c in self.subjects],
            outcomes=[c.with_context(do_rename, curie_to_name_map=curie_to_name_map, **context)
                      if c.name not in exclude_concepts else c
                      for c in self.outcomes],
            provenance=self.provenance,
            rate_law=self.rate_law,
        )


class ReversibleFlux(Template):
    """Specifies a reversible flux between a left and right side."""

    type: Literal["ReversibleFlux"] = "ReversibleFlux"
    left: List[Concept] = Field(..., description="The left hand side of the flux.")
    right: List[Concept] = Field(..., description="The right hand side of the flux.")
    provenance: List[Provenance] = Field(default_factory=list, description="The provenance of the flux.")

    concept_keys: ClassVar[List[str]] = ["left", "right"]

    def get_concepts(self):
        return self.left + self.right

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            *tuple(
                c.get_key(config=config)
                for c in sorted(self.left, key=lambda c: c.get_key(config=config))
            ),
            *tuple(
                c.get_key(config=config)
                for c in sorted(self.right, key=lambda c: c.get_key(config=config))
            ),
        )

    def with_context(
            self,
            do_rename=False,
            exclude_concepts=None,
            curie_to_name_map=None,
            **context
    ) -> "ReversibleFlux":
        exclude_concepts = exclude_concepts or set()
        return self.__class__(
            type=self.type,
            subjects=[c.with_context(do_rename, curie_to_name_map=curie_to_name_map, **context)
                      if c.name not in exclude_concepts else c
                      for c in self.left],
            outcomes=[c.with_context(do_rename, curie_to_name_map=curie_to_name_map, **context)
                      if c.name not in exclude_concepts else c
                      for c in self.right],
            provenance=self.provenance,
            rate_law=self.rate_law,
        )


class NaturalProduction(Template):
    """A template for the production of a species at a constant rate."""

    type: Literal["NaturalProduction"] = "NaturalProduction"
    outcome: Concept = Field(..., description="The outcome of the production.")
    provenance: List[Provenance] = Field(default_factory=list, description="The provenance of the production.")

    concept_keys: ClassVar[List[str]] = ["outcome"]

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.outcome.get_key(config=config),
        )

    def with_context(
        self,
        do_rename=False,
        exclude_concepts=None,
        curie_to_name_map=None,
        **context
    ) -> "NaturalProduction":
        exclude_concepts = exclude_concepts or set()
        return self.__class__(
            type=self.type,
            outcome=self.outcome.with_context(do_rename=do_rename,
                                              curie_to_name_map=curie_to_name_map,
                                              **context)
                if self.outcome.name not in exclude_concepts else self.outcome,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )


class NaturalDegradation(Template):
    """A template for the degradataion of a species at a proportional rate to its amount."""

    type: Literal["NaturalDegradation"] = "NaturalDegradation"
    subject: Concept = Field(..., description="The subject of the degradation.")
    provenance: List[Provenance] = Field(default_factory=list, description="The provenance of the degradation.")

    concept_keys: ClassVar[List[str]] = ["subject"]

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.subject.get_key(config=config),
        )

    def with_context(
        self,
        do_rename=False,
        exclude_concepts=None,
        curie_to_name_map=None,
        **context
    ) -> "NaturalDegradation":
        exclude_concepts = exclude_concepts or set()
        return self.__class__(
            type=self.type,
            subject=self.subject.with_context(
                do_rename=do_rename, curie_to_name_map=curie_to_name_map, **context
            ) if self.subject.name not in exclude_concepts else self.subject,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )


class ControlledDegradation(Template):
    """Specifies a process of degradation controlled by one controller"""

    type: Literal["ControlledDegradation"] = "ControlledDegradation"
    controller: Concept = Field(..., description="The controller of the degradation.")
    subject: Concept = Field(..., description="The subject of the degradation.")
    provenance: List[Provenance] = Field(default_factory=list, description="The provenance of the degradation.")

    concept_keys: ClassVar[List[str]] = ["controller", "subject"]

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.controller.get_key(config=config),
            self.subject.get_key(config=config),
        )

    def add_controller(self, controller: Concept) -> "GroupedControlledDegradation":
        """Add a controller to this template.

        Parameters
        ----------
        controller :
            The controller to add.

        Returns
        -------
        :
            A new template with the additional controller.
        """
        return GroupedControlledDegradation(
            subject=self.subject,
            controllers=[self.controller, controller],
            provenance=self.provenance,
        )

    def with_controller(self, controller) -> "ControlledDegradation":
        """Return a copy of this template with the given controller.

        Parameters
        ----------
        controller :
            The controller to use for the new template.

        Returns
        -------
        :
            A copy of this template as a ControlledDegradation template
            with the given controller replacing the existing controllers.
        """
        return self.__class__(
            type=self.type,
            controller=controller,
            subject=self.subject,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def with_context(
        self,
        do_rename=False,
        exclude_concepts=None,
        curie_to_name_map=None,
        **context
    ) -> "ControlledDegradation":
        exclude_concepts = exclude_concepts or set()
        return self.__class__(
            type=self.type,
            subject=self.subject.with_context(
                do_rename=do_rename, curie_to_name_map=curie_to_name_map, **context
            ) if self.subject.name not in exclude_concepts else self.subject,
            controller=self.controller.with_context(
                do_rename=do_rename, curie_to_name_map=curie_to_name_map, **context
            ) if self.controller.name not in exclude_concepts else self.controller,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )


class GroupedControlledDegradation(Template):
    """Specifies a process of degradation controlled by several controllers"""

    type: Literal["GroupedControlledDegradation"] = "GroupedControlledDegradation"
    controllers: List[Concept] = Field(..., description="The controllers of the degradation.")
    subject: Concept = Field(..., description="The subject of the degradation.")
    provenance: List[Provenance] = Field(default_factory=list, description="The provenance of the degradation.")

    concept_keys: ClassVar[List[str]] = ["controllers", "subject"]

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            *tuple(
                c.get_key(config=config)
                for c in sorted(self.controllers, key=lambda c: c.get_key(config=config))
            ),
            self.subject.get_key(config=config),
        )

    def get_concepts(self):
        return self.controllers + [self.subject]

    def add_controller(self, controller: Concept) -> "GroupedControlledDegradation":
        """Add a controller to this template.

        Parameters
        ----------
        controller :
            The controller to add.

        Returns
        -------
        :
            A new template with the additional controller added.
        """
        return GroupedControlledDegradation(
            subject=self.subject,
            provenance=self.provenance,
            controllers=[*self.controllers, controller]
        )

    def with_controllers(self, controllers) -> "GroupedControlledDegradation":
        """Return a copy of this template with the given controllers.

        Parameters
        ----------
        controllers :
            The controllers to use for the new template.

        Returns
        -------
        :
            A copy of this template with the given controllers replacing the
            existing controllers.
        """
        return self.__class__(
            type=self.type,
            controllers=controllers,
            subject=self.subject,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def with_context(
        self,
        do_rename=False,
        exclude_concepts=None,
        curie_to_name_map=None,
        **context
    ) -> "GroupedControlledDegradation":
        exclude_concepts = exclude_concepts or set()
        return self.__class__(
            type=self.type,
            controllers=[c.with_context(do_rename, curie_to_name_map=curie_to_name_map, **context)
                         if c.name not in exclude_concepts else c
                         for c in self.controllers],
            subject=self.subject.with_context(do_rename, curie_to_name_map=curie_to_name_map, **context)
                if self.subject.name not in exclude_concepts else self.subject,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )


class NaturalReplication(Template):
    """Specifies a process of natural replication of a subject."""

    type: Literal["NaturalReplication"] = "NaturalReplication"
    subject: Concept = Field(..., description="The subject of the replication.")
    provenance: List[Provenance] = Field(default_factory=list, description="The provenance of the template.")

    concept_keys: ClassVar[List[str]] = ["subject"]

    def with_context(
        self,
        do_rename=False,
        exclude_concepts=None,
        curie_to_name_map=None,
        **context
    ) -> "NaturalReplication":
        exclude_concepts = exclude_concepts or set()
        return self.__class__(
            type=self.type,
            subject=self.subject.with_context(
                do_rename=do_rename, curie_to_name_map=curie_to_name_map, **context
            ) if self.subject.name not in exclude_concepts else self.subject,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.subject.get_key(config=config),
        )


class ControlledReplication(Template):
    """Specifies a process of replication controlled by one controller"""

    type: Literal["ControlledReplication"] = "ControlledReplication"
    controller: Concept = Field(..., description="The controller of the replication.")
    subject: Concept = Field(..., description="The subject of the replication.")
    provenance: List[Provenance] = Field(default_factory=list, description="The provenance of the replication.")

    concept_keys: ClassVar[List[str]] = ["controller", "subject"]

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.controller.get_key(config=config),
            self.subject.get_key(config=config),
        )

    def with_controller(self, controller) -> "ControlledReplication":
        """Return a copy of this template with the given controller.

        Parameters
        ----------
        controller :
            The controller to use for the new template.

        Returns
        -------
        :
            A copy of this template with the given controller replacing the
            existing controller.
        """
        return self.__class__(
            type=self.type,
            controller=controller,
            subject=self.subject,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def with_context(
        self,
        do_rename=False,
        exclude_concepts=None,
        curie_to_name_map=None,
        **context
    ) -> "ControlledReplication":
        exclude_concepts = exclude_concepts or set()
        return self.__class__(
            type=self.type,
            subject=self.subject.with_context(
                do_rename=do_rename, curie_to_name_map=curie_to_name_map, **context
            ) if self.subject.name not in exclude_concepts else self.subject,
            controller=self.controller.with_context(
                do_rename=do_rename, curie_to_name_map=curie_to_name_map, **context
            ) if self.controller.name not in exclude_concepts else self.controller,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )


class StaticConcept(Template):
    """Specifies a standalone Concept that is not part of a process."""

    type: Literal["StaticConcept"] = "StaticConcept"
    subject: Concept = Field(..., description="The subject.")
    provenance: List[Provenance] = Field(default_factory=list, description="The provenance.")
    concept_keys: ClassVar[List[str]] = ["subject"]

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.subject.get_key(config=config),
        )

    def get_concepts(self):
        return [self.subject]

    def with_context(
        self,
        do_rename=False,
        curie_to_name_map=None,
        exclude_concepts=None,
        **context
    ) -> "StaticConcept":
        exclude_concepts = exclude_concepts or set()
        return self.__class__(
            type=self.type,
            subject=(self.subject.with_context(
                do_rename, curie_to_name_map=curie_to_name_map, **context
            ) if self.subject.name not in exclude_concepts else self.subject),
            provenance=self.provenance,
            rate_law=self.rate_law,
        )


def templates_equal(templ: Template, other_templ: Template, with_context: bool,
                    config: Config) -> bool:
    """Check if two Template objects are equal

    Parameters
    ----------
    templ :
        A template to compare.
    other_templ :
        The other template to compare.
    with_context :
        If True, also check the contexts of the contained Concepts of the
        Template.
    config :
        Configuration defining priority and exclusion for identifiers.

    Returns
    -------
    :
        True if the two Template objects are equal.
    """
    if templ.type != other_templ.type:
        return False

    other_by_role = other_templ.get_concepts_by_role()
    for role, value in templ.get_concepts_by_role().items():
        other_value = other_by_role.get(role)
        if isinstance(value, Concept):
            if not value.is_equal_to(other_value, with_context=with_context,
                                     config=config):
                return False
        elif isinstance(value, list):
            if len(value) != len(other_value):
                return False

            if not match_concepts(value, other_value,
                                  with_context=with_context,
                                  config=config):
                return False
    return True


def match_concepts(
    self_concepts: List[Concept],
    other_concepts: List[Concept],
    with_context: bool = True,
    config: Config = None,
    refinement_func: Callable[[str, str], bool] = None,
) -> bool:
    """Return true if there is an exact match between two lists of concepts.

    Parameters
    ----------
    self_concepts :
        The list of concepts to compare to the second list.
    other_concepts :
        The second list of concepts to compare the first list to.
    with_context :
        If True, also consider the contexts of the contained Concepts of the
        Template when comparing the two lists. Default: True.
    config :
        Configuration defining priority and exclusion for identifiers. If None,
        the default configuration will be used.
    refinement_func :
        A function to use to check if one concept is a refinement of another.
        If None, the default is to check for equality.

    Returns
    -------
    :
        True if there is an exact match between the two lists of concepts.
    """
    # First build a bipartite graph of matches
    G = nx.Graph()
    for (self_idx, self_concept), (other_idx, other_concept) in \
            product(enumerate(self_concepts), enumerate(other_concepts)):
        if refinement_func:
            res = self_concept.refinement_of(other_concept,
                                             with_context=with_context,
                                             refinement_func=refinement_func,
                                             config=config)
        else:
            res = self_concept.is_equal_to(other_concept,
                                           with_context=with_context,
                                           config=config)
        if res:
            G.add_edge('S%d' % self_idx, 'O%d' % other_idx)
    # Then find a maximal matching in the bipartite graph
    match = nx.algorithms.max_weight_matching(G)
    # If all the other concepts are covered, this is considered a match.
    # The reason for checking this as a condition is that this works for
    # both the equality case where the two lists have the same length, and
    # the refinement case where we want to find a match/refinement for
    # each of the concepts in the other list.
    return len(match) == len(other_concepts)


def context_refinement(refined_context, other_context) -> bool:
    """Check if one Concept's context is a refinement of another Concept's

    Parameters
    ----------
    refined_context :
        The assumed *more* detailed context
    other_context :
        The assumed *less* detailed context

    Returns
    -------
    :
        True if the Concept `refined_concept` truly is strictly more detailed
        than `other_concept`
    """
    # 1. True if no context for both
    if not refined_context and not other_context:
        return True
    # 2. True if refined concept has context and the other one not
    elif refined_context and not other_context:
        return True
    # 3. False if refined concept does not have context and the other does
    elif not refined_context and other_context:
        return False
    # 4. Both have context, in which case we need to make sure there is no
    # explicit difference for any key/value pair that exists in other. This
    # means that the refined context can have additional keys/values, or
    # the two contexts can be exactly equal
    else:
        for other_key, other_val in other_context.items():
            if refined_context.get(other_key) != other_val:
                return False
    return True


# Needed for proper parsing by FastAPI
SpecifiedTemplate = Annotated[
    Union[
        NaturalConversion,
        MultiConversion,
        ControlledConversion,
        NaturalDegradation,
        ControlledDegradation,
        GroupedControlledDegradation,
        NaturalProduction,
        ControlledProduction,
        GroupedControlledConversion,
        GroupedControlledProduction,
        NaturalReplication,
        ControlledReplication,
        StaticConcept,
        ReversibleFlux,
    ],
    Field(description="Any child class of a Template", discriminator="type"),
]


def has_specific_controller(template: Template, controller: Concept) -> bool:
    """Check if the template has a given controller.

    Parameters
    ----------
    template :
        The template to check. The template must be representing a controlled
        process.
    controller
        The controller to check for

    Returns
    -------
    :
        True if the template has the given controller

    Raises
    ------
    NotImplementedError
        If the template is not a controlled process.
    """
    concepts_by_role = template.get_concepts_by_role()
    if 'controller' in concepts_by_role:
        return template.controller == controller
    elif 'controllers' in concepts_by_role:
        return any(c == controller for c in template.controllers)
    else:
        raise NotImplementedError(
            f"Template {template.type} is not a controlled process"
        )


def has_controller(template: Template) -> bool:
    """Check if the template has a controller.

    Parameters
    ----------
    template :
        The template to check. The template must be representing a controlled
        process.

    Returns
    -------
    :
        True if the template has a controller
    """
    if {'controller', 'controllers'} & set(template.get_concepts_by_role()):
        return True
    else:
        return False


def is_production(template):
    """Return True if the template is a form of production."""
    return isinstance(template, (NaturalProduction, ControlledProduction,
                                 GroupedControlledProduction))


def is_degradation(template):
    """Return True if the template is a form of degradation."""
    return isinstance(template, (NaturalDegradation, ControlledDegradation,
                                 GroupedControlledDegradation))


def is_replication(template):
    """Return True if the template is a form of replication."""
    return isinstance(template, (NaturalReplication, ControlledReplication))


def is_conversion(template):
    """Return True if the template is a form of conversion."""
    return isinstance(template, (NaturalConversion, ControlledConversion,
                                 GroupedControlledConversion, MultiConversion))


def has_outcome(template):
    """Return True if the template has an outcome."""
    return is_production(template) or is_conversion(template)


def has_subject(template):
    """Return True if the template has a subject."""
    return (is_conversion(template) or is_degradation(template)
            or is_replication(template))


def is_reversible(template):
    """Return True if the template is a reversible process."""
    return isinstance(template, ReversibleFlux)


def num_controllers(template):
    """Return the number of controllers in the template."""
    if isinstance(template, (ControlledConversion,
                             ControlledProduction,
                             ControlledDegradation,
                             ControlledReplication)):
        return 1
    elif isinstance(template, (GroupedControlledConversion,
                               GroupedControlledProduction,
                               GroupedControlledDegradation)):
        return len(template.controllers)
    else:
        return 0


def get_binding_templates(a, b, c, kf, kr):
    """Return a list of templates emulating a reversible binding process."""
    af = lambda: Concept(name=a)
    bf = lambda: Concept(name=b)
    cf = lambda: Concept(name=c)
    templates = [
        GroupedControlledProduction(controllers=[af(), bf()],
                                    outcome=cf()).with_mass_action_rate_law(kf),
        ControlledDegradation(controller=af(),
                              subject=bf()).with_mass_action_rate_law(kf),
        ControlledDegradation(controller=bf(),
                              subject=af()).with_mass_action_rate_law(kf),
        NaturalDegradation(subject=cf()).with_mass_action_rate_law(kr),
        ControlledProduction(controller=cf(),
                             outcome=af()).with_mass_action_rate_law(kr),
        ControlledProduction(controller=cf(),
                             outcome=bf()).with_mass_action_rate_law(kr)
    ]
    return templates


def conversion_to_deg_prod(conv_template):
    # TODO: Handle multiconversion
    """Given a conversion template, compile into degradation/production templates."""
    if not is_conversion(conv_template):
        return [conv_template]
    nc = num_controllers(conv_template)
    if nc == 0:
        tdeg = NaturalDegradation(subject=conv_template.subject,
                                  rate_law=conv_template.rate_law)
        tprod = ControlledProduction(outcome=conv_template.outcome,
                                     controller=conv_template.subject,
                                     rate_law=conv_template.rate_law)
    elif nc == 1:
        tdeg = ControlledDegradation(subject=conv_template.subject,
                                     controller=conv_template.controller,
                                     rate_law=conv_template.rate_law)
        tprod = GroupedControlledProduction(outcome=conv_template.outcome,
                                            controllers=[conv_template.controller,
                                                         conv_template.subject],
                                            rate_law=conv_template.rate_law)
    else:
        tdeg = GroupedControlledDegradation(subject=conv_template.subject,
                                            controllers=conv_template.controllers,
                                            rate_law=conv_template.rate_law)
        tprod = GroupedControlledProduction(outcome=conv_template.outcome,
                                            controllers=conv_template.controllers +
                                                        [conv_template.subject],
                                            rate_law=conv_template.rate_law)
    return deepcopy([tdeg, tprod])
