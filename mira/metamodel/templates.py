"""
Data models for metamodel templates.

Regenerate the JSON schema by running ``python -m mira.metamodel.templates``.
"""
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
    "SpecifiedTemplate",
    "templates_equal",
    "context_refinement",
]

import logging
import sys
from collections import ChainMap
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
from pydantic import BaseModel, Field

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

    prefix_priority: List[str]
    prefix_exclusions: List[str]


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
    display_name: str = \
        Field(None, description="An optional display name for the concept. "
                                "If not provided, the name can be used for "
                                "display purposes.")
    description: Optional[str] = \
        Field(None, description="An optional description of the concept.")
    identifiers: Mapping[str, str] = Field(
        default_factory=dict, description="A mapping of namespaces to identifiers."
    )
    context: Mapping[str, str] = Field(
        default_factory=dict, description="A mapping of context keys to values."
    )
    units: Optional[Unit] = Field(
        None, description="The units of the concept."
    )
    _base_name: str = pydantic.PrivateAttr(None)

    def with_context(self, do_rename=False, **context) -> "Concept":
        """Return this concept with extra context.

        Parameters
        ----------
        do_rename :
            If true, will modify the name of the node based on the context
            introduced

        Returns
        -------
        :
            A new concept containing the given context.
        """
        if do_rename:
            if self._base_name is None:
                self._base_name = self.name
            name = '_'.join([self._base_name] + [str(v) for _, v in sorted(context.items())])
        else:
            name = self.name
        concept = Concept(
            name=name,
            identifiers=self.identifiers,
            context=dict(ChainMap(context, self.context)),
            units=self.units,
        )
        concept._base_name = self._base_name
        return concept

    def get_curie(self, config: Optional[Config] = None) -> Tuple[str, str]:
        """Get the priority prefix/identifier pair for this concept."""
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
        """Get the priority prefix/identifier as a CURIE string."""
        return ":".join(self.get_curie(config=config))

    def get_included_identifiers(self, config: Optional[Config] = None) -> Dict[str, str]:
        config = DEFAULT_CONFIG if config is None else config
        return {k: v for k, v in self.identifiers.items() if k not in config.prefix_exclusions}

    def get_key(self, config: Optional[Config] = None):
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


class Template(BaseModel):
    """The Template is a parent class for model processes"""

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            SympyExprStr: lambda e: str(e),
        }
        json_decoders = {
            SympyExprStr: lambda e: safe_parse_expr(e)
        }

    rate_law: Optional[SympyExprStr] = Field(default=None)

    @classmethod
    def from_json(cls, data, rate_symbols=None) -> "Template":
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
        return stmt_cls(**{k: v for k, v in data.items()
                           if k not in {'rate_law', 'type'}},
                        rate_law=rate)

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

    def get_concepts(self):
        """Return the concepts in this template."""
        return [getattr(self, k) for k in self.concept_keys]

    def get_concepts_by_role(self):
        """Return the concepts in this template as a dict keyed by role."""
        return {
            k: getattr(self, k) for k in self.concept_keys
        }

    def get_concept_names(self):
        """Return the concept names in this template."""
        return {c.name for c in self.get_concepts()}

    def get_interactors(self) -> List[Concept]:
        """Return the interactors in this template."""
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

    def get_controllers(self):
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

    def get_independent_mass_action_rate_law(self, parameter: str):
        rate_law = sympy.Symbol(parameter) * \
            self.get_interactor_rate_law(independent=True)
        return rate_law

    def set_mass_action_rate_law(self, parameter, independent=False):
        """Set the rate law of this template to a mass action rate law.

        Parameters
        ----------
        parameter :
            The parameter to use for the mass-action rate.
        """
        self.rate_law = SympyExprStr(
            self.get_mass_action_rate_law(parameter, independent=independent))

    def get_parameter_names(self) -> Set[str]:
        """Get the set of parameter names."""
        if not self.rate_law:
            return set()
        return (
            {s.name for s in self.rate_law.args[0].free_symbols}
            - self.get_concept_names()
        )

    def update_parameter_name(self, old_name, new_name):
        """Update the name of a parameter in the rate law."""
        if self.rate_law:
            self.rate_law = self.rate_law.subs(sympy.Symbol(old_name),
                                               sympy.Symbol(new_name))

    def get_mass_action_symbol(self) -> Optional[sympy.Symbol]:
        """Get the symbol for the parameter associated with this template's rate law,
        assuming it's mass action."""
        if not self.rate_law:
            return None
        results = sorted(self.get_parameter_names())
        if not results:
            return None
        if len(results) == 1:
            return sympy.Symbol(results[0])
        raise ValueError("recovered multiple parameters - not mass action")

    def substitute_parameter(self, name, value):
        """Substitute a parameter in this template's rate law."""
        if not self.rate_law:
            return
        self.rate_law = SympyExprStr(
            self.rate_law.args[0].subs(sympy.Symbol(name), value))


class Provenance(BaseModel):
    pass


class ControlledConversion(Template):
    """Specifies a process of controlled conversion from subject to outcome,
    controlled by the controller."""

    type: Literal["ControlledConversion"] = Field("ControlledConversion", const=True)
    controller: Concept
    subject: Concept
    outcome: Concept
    provenance: List[Provenance] = Field(default_factory=list)

    concept_keys: ClassVar[List[str]] = ["controller", "subject", "outcome"]

    def with_context(self, do_rename=False, **context) -> "ControlledConversion":
        """Return a copy of this template with context added"""
        return self.__class__(
            type=self.type,
            subject=self.subject.with_context(do_rename=do_rename, **context),
            outcome=self.outcome.with_context(do_rename=do_rename, **context),
            controller=self.controller.with_context(do_rename=do_rename, **context),
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def add_controller(self, controller: Concept) -> "GroupedControlledConversion":
        """Add an additional controller."""
        return GroupedControlledConversion(
            subject=self.subject,
            outcome=self.outcome,
            provenance=self.provenance,
            controllers=[self.controller, controller]
        )

    def with_controller(self, controller) -> "ControlledConversion":
        """Return a copy of this template with the given controller."""
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
    type: Literal["GroupedControlledConversion"] = Field("GroupedControlledConversion", const=True)
    controllers: List[Concept]
    subject: Concept
    outcome: Concept
    provenance: List[Provenance] = Field(default_factory=list)

    concept_keys: ClassVar[List[str]] = ["controllers", "subject", "outcome"]

    def with_context(self, do_rename=False, **context) -> "GroupedControlledConversion":
        """Return a copy of this template with context added"""
        return self.__class__(
            type=self.type,
            controllers=[c.with_context(do_rename, **context) for c in self.controllers],
            subject=self.subject.with_context(do_rename, **context),
            outcome=self.outcome.with_context(do_rename, **context),
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def with_controllers(self, controllers) -> "GroupedControlledConversion":
        """Return a copy of this template with the given controllers."""
        if len(self.controllers) != len(controllers):
            raise ValueError
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
        """Return the concepts in this template."""
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

    type: Literal["GroupedControlledProduction"] = Field("GroupedControlledProduction", const=True)
    controllers: List[Concept]
    outcome: Concept
    provenance: List[Provenance] = Field(default_factory=list)

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
        """Return a list of the concepts in this template"""
        return self.controllers + [self.outcome]

    def add_controller(self, controller: Concept) -> "GroupedControlledProduction":
        """Add an additional controller."""
        return GroupedControlledProduction(
            outcome=self.outcome,
            provenance=self.provenance,
            controllers=[*self.controllers, controller]
        )

    def with_controllers(self, controllers) -> "GroupedControlledProduction":
        """Return a copy of this template with the given controllers."""
        return self.__class__(
            type=self.type,
            controllers=controllers,
            outcome=self.outcome,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def with_context(self, do_rename=False, **context) -> "GroupedControlledProduction":
        """Return a copy of this template with context added"""
        return self.__class__(
            type=self.type,
            controllers=[c.with_context(do_rename, **context) for c in self.controllers],
            outcome=self.outcome.with_context(do_rename, **context),
            provenance=self.provenance,
            rate_law=self.rate_law,
        )



class ControlledProduction(Template):
    """Specifies a process of production controlled by one controller"""

    type: Literal["ControlledProduction"] = Field("ControlledProduction", const=True)
    controller: Concept
    outcome: Concept
    provenance: List[Provenance] = Field(default_factory=list)

    concept_keys: ClassVar[List[str]] = ["controller", "outcome"]

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.controller.get_key(config=config),
            self.outcome.get_key(config=config),
        )

    def add_controller(self, controller: Concept) -> "GroupedControlledProduction":
        """Add an additional controller."""
        return GroupedControlledProduction(
            outcome=self.outcome,
            provenance=self.provenance,
            controllers=[self.controller, controller]
        )

    def with_controller(self, controller) -> "ControlledProduction":
        """Return a copy of this template with the given controller."""
        return self.__class__(
            type=self.type,
            controller=controller,
            outcome=self.outcome,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def with_context(self, do_rename=False, **context) -> "ControlledProduction":
        """Return a copy of this template with context added"""
        return self.__class__(
            type=self.type,
            outcome=self.outcome.with_context(do_rename=do_rename, **context),
            controller=self.controller.with_context(do_rename=do_rename, **context),
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

class NaturalConversion(Template):
    """Specifies a process of natural conversion from subject to outcome"""

    type: Literal["NaturalConversion"] = Field("NaturalConversion", const=True)
    subject: Concept
    outcome: Concept
    provenance: List[Provenance] = Field(default_factory=list)

    concept_keys: ClassVar[List[str]] = ["subject", "outcome"]

    def with_context(self, do_rename=False, **context) -> "NaturalConversion":
        """Return a copy of this template with context added"""
        return self.__class__(
            type=self.type,
            subject=self.subject.with_context(do_rename=do_rename, **context),
            outcome=self.outcome.with_context(do_rename=do_rename, **context),
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.subject.get_key(config=config),
            self.outcome.get_key(config=config),
        )


class NaturalProduction(Template):
    """A template for the production of a species at a constant rate."""

    type: Literal["NaturalProduction"] = Field("NaturalProduction", const=True)
    outcome: Concept
    provenance: List[Provenance] = Field(default_factory=list)

    concept_keys: ClassVar[List[str]] = ["outcome"]

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.outcome.get_key(config=config),
        )

    def with_context(self, do_rename=False, **context) -> "NaturalProduction":
        """Return a copy of this template with context added"""
        return self.__class__(
            type=self.type,
            outcome=self.outcome.with_context(do_rename=do_rename, **context),
            provenance=self.provenance,
            rate_law=self.rate_law,
        )


class NaturalDegradation(Template):
    """A template for the degradataion of a species at a proportional rate to its amount."""

    type: Literal["NaturalDegradation"] = Field("NaturalDegradation", const=True)
    subject: Concept
    provenance: List[Provenance] = Field(default_factory=list)

    concept_keys: ClassVar[List[str]] = ["subject"]

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.subject.get_key(config=config),
        )

    def with_context(self, do_rename=False, **context) -> "NaturalDegradation":
        """Return a copy of this template with context added"""
        return self.__class__(
            type=self.type,
            subject=self.subject.with_context(do_rename=do_rename, **context),
            provenance=self.provenance,
            rate_law=self.rate_law,
        )


class ControlledDegradation(Template):
    """Specifies a process of degradation controlled by one controller"""

    type: Literal["ControlledDegradation"] = Field("ControlledDegradation", const=True)
    controller: Concept
    subject: Concept
    provenance: List[Provenance] = Field(default_factory=list)

    concept_keys: ClassVar[List[str]] = ["controller", "subject"]

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.controller.get_key(config=config),
            self.subject.get_key(config=config),
        )

    def add_controller(self, controller: Concept) -> "GroupedControlledDegradation":
        """Add an additional controller."""
        return GroupedControlledDegradation(
            subject=self.subject,
            controllers=[self.controller, controller],
            provenance=self.provenance,
        )

    def with_controller(self, controller) -> "ControlledDegradation":
        """Return a copy of this template with the given controller."""
        return self.__class__(
            type=self.type,
            controller=controller,
            subject=self.subject,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def with_context(self, do_rename=False, **context) -> "ControlledDegradation":
        """Return a copy of this template with context added"""
        return self.__class__(
            type=self.type,
            subject=self.subject.with_context(do_rename=do_rename, **context),
            controller=self.controller.with_context(do_rename=do_rename, **context),
            provenance=self.provenance,
            rate_law=self.rate_law,
        )


class GroupedControlledDegradation(Template):
    """Specifies a process of degradation controlled by several controllers"""

    type: Literal["GroupedControlledDegradation"] = Field("GroupedControlledDegradation", const=True)
    controllers: List[Concept]
    subject: Concept
    provenance: List[Provenance] = Field(default_factory=list)

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
        """Return a list of the concepts in this template"""
        return self.controllers + [self.subject]

    def add_controller(self, controller: Concept) -> "GroupedControlledDegradation":
        """Add an additional controller."""
        return GroupedControlledDegradation(
            subject=self.subject,
            provenance=self.provenance,
            controllers=[*self.controllers, controller]
        )

    def with_controllers(self, controllers) -> "GroupedControlledDegradation":
        """Return a copy of this template with the given controllers."""
        return self.__class__(
            type=self.type,
            controllers=controllers,
            subject=self.subject,
            provenance=self.provenance,
            rate_law=self.rate_law,
        )

    def with_context(self, do_rename=False, **context) -> "GroupedControlledDegradation":
        """Return a copy of this template with context added"""
        return self.__class__(
            type=self.type,
            controllers=[c.with_context(do_rename, **context) for c in self.controllers],
            subject=self.subject.with_context(do_rename, **context),
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


def match_concepts(self_concepts, other_concepts, with_context=True,
                   config=None, refinement_func=None):
    """Return true if there is an exact match between two lists of concepts."""
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
        ControlledConversion,
        NaturalDegradation,
        ControlledDegradation,
        GroupedControlledDegradation,
        NaturalProduction,
        ControlledProduction,
        GroupedControlledConversion,
        GroupedControlledProduction,
    ],
    Field(description="Any child class of a Template", discriminator="type"),
]


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
