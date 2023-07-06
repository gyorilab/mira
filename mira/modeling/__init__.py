__all__ = ["Model", "Transition", "Variable", "ModelParameter"]

import logging
from typing import Dict, Hashable, Mapping, Optional

from mira.metamodel import *

logger = logging.getLogger(__name__)


class Transition:
    def __init__(
        self, key, consumed, produced, control, rate, template_type, template: Template,
    ):
        self.key = key
        self.consumed = consumed
        self.produced = produced
        self.control = control
        self.rate = rate
        self.template_type = template_type
        self.template = template


class Variable:
    def __init__(self, key, data, concept: Concept):
        self.key = key
        self.data = data
        self.concept = concept


class ModelParameter:
    def __init__(self, key, value=None, distribution=None, placeholder=None,
                 concept=None):
        self.key = key
        self.value = value
        self.distribution = distribution
        self.placeholder = placeholder
        self.concept = concept


class ModelObservable:
    def __init__(self, observable, parameters):
        self.observable = observable
        self.parameters = parameters


def get_transition_key(concept_keys, action):
    return concept_keys + (action,)


def get_parameter_key(transition_key, action):
    return transition_key + (action,)


UNHANDLED_TYPES = set()


class Model:
    def __init__(self, template_model):
        self.template_model = template_model
        self.variables: Dict[Hashable, Variable] = {}
        self.parameters: Dict[Hashable, ModelParameter] = {}
        self.transitions: Dict[Hashable, Transition] = {}
        self.observables: Dict[Hashable, ModelObservable] = {}
        self.make_model()

    def assemble_variable(
        self, concept: Concept, initials: Optional[Mapping[str, Initial]] = None,
    ):
        """Assemble a variable from a concept and optional
        dictionary of initial values.

        Parameters
        ----------
        concept :
            The concept for the variable
        initials :
            A dictionary mapping from names of concepts to objects
            representing their initial values

        Returns
        -------
        A variable object, representing a concept and its initial value
        """
        grounding_key = sorted(
            ("identity", f"{k}:{v}")
            for k, v in concept.get_included_identifiers().items()
        )
        context_key = sorted(concept.context.items())
        key = [concept.name] + grounding_key + context_key
        key = tuple(key) if len(key) > 1 else key[0]
        if key in self.variables:
            return self.variables[key]

        if initials and concept.name in initials:
            initial_value = initials[concept.name].value
        else:
            initial_value = None

        data = {
            'name': concept.name,
            'identifiers': grounding_key,
            'context': context_key,
            'initial_value': initial_value
        }
        var = Variable(key, data=data, concept=concept)
        self.variables[key] = var
        return var

    def assemble_parameter(self, template: Template, tkey) -> ModelParameter:
        rate_parameters = sorted(
            self.template_model.get_parameters_from_rate_law(template.rate_law))

        if rate_parameters:
            model_parameters = []
            for key in rate_parameters:
                param = self.template_model.parameters[key]
                model_parameters.append(
                    self.get_create_parameter(
                        ModelParameter(key, param.value, param.distribution,
                                       placeholder=False,
                                       concept=param)))
            if len(model_parameters) == 1:
                return model_parameters[0]

        # add in an implied mass action parameter, applicable
        # both if there are no rate parameters or if there are
        # more than one
        value = None
        key = get_parameter_key(tkey, 'rate')
        return self.get_create_parameter(ModelParameter(key, value,
                                                        placeholder=True))

    def make_model(self):
        for name, observable in self.template_model.observables.items():
            params = sorted(
                observable.get_parameter_names(self.template_model.parameters))
            self.observables[observable.name] = \
                ModelObservable(observable, params)
            for key in params:
                value = self.template_model.parameters[key].value
                distribution = self.template_model.parameters[key].distribution
                self.get_create_parameter(
                        ModelParameter(key, value, distribution,
                                       placeholder=False))

        for template in self.template_model.templates:
            # Handle subjects
            if has_subject(template):
                s = self.assemble_variable(template.subject,
                                           self.template_model.initials)
                consumed, consumed_key = (s,), s.key
            else:
                consumed, consumed_key = tuple(), None

            # Handle controllers
            if num_controllers(template) == 1:
                c = self.assemble_variable(template.controller,
                                           self.template_model.initials)
                control = (c,)
                control_key = c.key
            elif num_controllers(template) > 1:
                control = tuple(
                    self.assemble_variable(controller,
                                           self.template_model.initials)
                    for controller in template.controllers
                )
                control_key = tuple(c.key for c in control)
            else:
                control = tuple()
                control_key = None

            # Handle outcomes
            if has_outcome(template):
                o = self.assemble_variable(template.outcome,
                                           self.template_model.initials)
                produced, produced_key = (o,), o.key
            else:
                produced, produced_key = tuple(), None

            tkey_elements = tuple(
                element for element in [consumed_key, produced_key, control_key]
                if element is not None
            )
            tkey = get_transition_key(tkey_elements, template.type)

            p = self.assemble_parameter(template, tkey)
            self.get_create_transition(Transition(
                tkey,
                consumed=consumed,
                produced=produced,
                control=control,
                rate=p,
                template_type=template.type,
                template=template,
            ))

    def get_create_parameter(self, parameter: ModelParameter) -> ModelParameter:
        if parameter.key not in self.parameters:
            self.parameters[parameter.key] = parameter
        return self.parameters[parameter.key]

    def get_create_transition(self, transition: Transition) -> Transition:
        if transition.key not in self.transitions:
            self.transitions[transition.key] = transition
        return self.transitions[transition.key]


def is_production(template):
    return isinstance(template, (NaturalProduction, ControlledProduction,
                                 GroupedControlledProduction))


def is_degradation(template):
    return isinstance(template, (NaturalDegradation, ControlledDegradation,
                                 GroupedControlledDegradation))


def is_conversion(template):
    return isinstance(template, (NaturalConversion, ControlledConversion,
                                 GroupedControlledConversion))


def has_outcome(template):
    return is_production(template) or is_conversion(template)


def has_subject(template):
    return is_conversion(template) or is_degradation(template)


def num_controllers(template):
    if isinstance(template, (ControlledConversion,
                             ControlledProduction,
                             ControlledDegradation)):
        return 1
    elif isinstance(template, (GroupedControlledConversion,
                               GroupedControlledProduction,
                               GroupedControlledDegradation)):
        return len(template.controllers)
    else:
        return 0

