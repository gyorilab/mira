__all__ = ["TemplateModel", "Model", "Transition", "Variable", "Parameter"]

import logging
from typing import List, Union

from pydantic import BaseModel, Field

from mira.metamodel import (
    ControlledConversion, NaturalConversion, Template, NaturalProduction, NaturalDegradation,
    GroupedControlledConversion,
)

try:
    from typing import Annotated  # py39+
except ImportError:
    from typing_extensions import Annotated

logger = logging.getLogger(__name__)

# Needed for proper parsing by FastAPI
SpecifiedTemplate = Annotated[
    Union[
        NaturalConversion, ControlledConversion, NaturalDegradation, NaturalProduction, GroupedControlledConversion,
    ],
    Field(description="Any child class of a Template", discriminator="type"),
]


class TemplateModel(BaseModel):
    templates: List[SpecifiedTemplate] = Field(
        ..., description="A list of any child class of Templates"
    )

    @classmethod
    def from_json(cls, data) -> "TemplateModel":
        templates = [Template.from_json(template) for template in data["templates"]]
        return cls(templates=templates)


class Transition:
    def __init__(self, key, consumed, produced, control, rate):
        self.key = key
        self.consumed = consumed
        self.produced = produced
        self.control = control
        self.rate = rate


# TODO is there a reason this can't contain the base concept from which it was derived?
class Variable:
    def __init__(self, key):
        self.key = key


class Parameter:
    def __init__(self, key):
        self.key = key


def get_variable_key(concept):
    return (
        concept.name,
        tuple(sorted(("identity", f"{k}:{v}") for k, v in concept.identifiers.items() if k != "biomodel.species")),
        tuple(sorted(concept.context.items())),
    )


def get_transition_key(concept_keys, action):
    return concept_keys + (action,)


def get_parameter_key(transition_key, action):
    return transition_key + (action,)


UNHANDLED_TYPES = set()


class Model:
    def __init__(self, template_model):
        self.template_model = template_model
        self.variables = {}
        self.parameters = {}
        self.transitions = {}
        self.make_model()

    def make_model(self):
        for template in self.template_model.templates:
            if isinstance(template, (NaturalConversion, NaturalProduction, NaturalDegradation)):
                if isinstance(template, (NaturalConversion, NaturalDegradation)):
                    s = self.get_create_variable(
                        Variable(get_variable_key(template.subject)))
                    consumed = (s,)
                else:
                    consumed = tuple()
                if isinstance(template, (NaturalConversion, NaturalProduction)):
                    o = self.get_create_variable(
                        Variable(get_variable_key(template.outcome)))
                    produced= (o,)
                else:
                    produced = tuple()
                tkey = get_transition_key(
                    (
                        tuple(s.key for s in consumed),
                        tuple(o.key for o in produced),
                    ),
                    template.type,
                )
                p = self.get_create_parameter(
                    Parameter(get_parameter_key(tkey, 'rate')))
                self.get_create_transition(Transition(
                    tkey,
                    consumed=consumed,
                    produced=produced,
                    control=tuple(),
                    rate=p,
                ))
            elif isinstance(template, (ControlledConversion, GroupedControlledConversion)):
                s = self.get_create_variable(
                    Variable(get_variable_key(template.subject)))
                o = self.get_create_variable(
                    Variable(get_variable_key(template.outcome)))

                if isinstance(template, ControlledConversion):
                    c = self.get_create_variable(
                        Variable(get_variable_key(template.controller)))
                    control = (c,)
                    tkey = get_transition_key((s.key, o.key, (c.key,)), template.type)
                else:
                    control = tuple(
                        self.get_create_variable(Variable(get_variable_key(controller)))
                        for controller in template.controllers
                    )
                    tkey = get_transition_key((s.key, o.key, tuple(c.key for c in control)), template.type)

                p = self.get_create_parameter(
                    Parameter(get_parameter_key(tkey, 'rate')))
                self.get_create_transition(Transition(
                    tkey,
                    consumed=(s,),
                    produced=(o,),
                    control=control,
                    rate=p,
                ))
            else:
                if template.__class__ not in UNHANDLED_TYPES:
                    logger.warning("unhandled template type: %s", template.__class__)
                    UNHANDLED_TYPES.add(template.__class__)

    def get_create_variable(self, variable):
        if variable.key not in self.variables:
            self.variables[variable.key] = variable
        return self.variables[variable.key]

    def get_create_parameter(self, parameter):
        if parameter.key not in self.parameters:
            self.parameters[parameter.key] = parameter
        return self.parameters[parameter.key]

    def get_create_transition(self, transition):
        if transition.key not in self.transitions:
            self.transitions[transition.key] = transition
        return self.transitions[transition.key]
