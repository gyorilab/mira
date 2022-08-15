__all__ = ["TemplateModel", "Model", "Transition", "Variable", "Parameter"]

from typing import List

from pydantic import BaseModel

from mira.metamodel import ControlledConversion, NaturalConversion, Template


class TemplateModel(BaseModel):
    templates: List[Template]

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
    if concept.context:
        return concept.name, *sorted(concept.context.items())
    return concept.name


def get_transition_key(concept_keys, action):
    return concept_keys + (action,)


def get_parameter_key(transition_key, action):
    return transition_key + (action,)


class Model:
    def __init__(self, template_model):
        self.template_model = template_model
        self.variables = {}
        self.parameters = {}
        self.transitions = {}
        self.make_model()

    def make_model(self):
        for template in self.template_model.templates:
            if isinstance(template, NaturalConversion):
                s = self.get_create_variable(
                    Variable(get_variable_key(template.subject)))
                o = self.get_create_variable(
                    Variable(get_variable_key(template.outcome)))
                tkey = get_transition_key((s.key, o.key), template.type)
                p = self.get_create_parameter(
                    Parameter(get_parameter_key(tkey, 'rate')))
                self.get_create_transition(Transition(tkey,
                                                      consumed=(s,),
                                                      produced=(o,),
                                                      control=tuple(),
                                                      rate=p)
                                            )
            elif isinstance(template, ControlledConversion):
                s = self.get_create_variable(
                    Variable(get_variable_key(template.subject)))
                o = self.get_create_variable(
                    Variable(get_variable_key(template.outcome)))
                c = self.get_create_variable(
                    Variable(get_variable_key(template.controller)))
                tkey = get_transition_key((s.key, o.key, c.key), template.type)
                p = self.get_create_parameter(
                    Parameter(get_parameter_key(tkey, 'rate')))
                self.get_create_transition(Transition(tkey,
                                                      consumed=(s,),
                                                      produced=(o,),
                                                      control=(c,),
                                                      rate=p)
                                            )

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