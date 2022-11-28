__all__ = ["Model", "Transition", "Variable", "ModelParameter"]

import logging
import math

from mira.metamodel import (
    ControlledConversion, NaturalConversion, NaturalProduction,
    NaturalDegradation, GroupedControlledConversion,
    GroupedControlledProduction,
)


logger = logging.getLogger(__name__)


class Transition:
    def __init__(self, key, consumed, produced, control, rate, template_type):
        self.key = key
        self.consumed = consumed
        self.produced = produced
        self.control = control
        self.rate = rate
        self.template_type = template_type


class Variable:
    def __init__(self, key, data=None):
        self.key = key
        self.data = data


class ModelParameter:
    def __init__(self, key, value=None):
        self.key = key
        self.value = value


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

    def assemble_variable(self, concept, initials=None):
        grounding_key = sorted(
            ("identity", f"{k}:{v}")
            for k, v in concept.get_included_identifiers().items()
        )
        context_key = sorted(concept.context.items())
        key = [concept.name] + grounding_key + context_key
        key = tuple(key) if len(key) > 1 else key[0]
        if key in self.variables:
            return self.variables[key]

        if initials:
            initial_value = initials.get(concept.name)
        else:
            initial_value = None

        data = {
            'name': concept.name,
            'identifiers': grounding_key,
            'context': context_key,
            'initial_value': initial_value
        }
        var = Variable(key, data)
        self.variables[key] = var
        return var

    def assemble_parameter(self, template, tkey):
        rate_parameters = self.template_model.get_parameters_from_rate_law(
            template.rate_law)
        if len(rate_parameters) == 1:
            key = list(rate_parameters)[0]
            value = self.template_model.parameters[key].value
        # TODO: Relax assumption here that the overall parameter is a product
        #elif len(rate_parameters) > 1:
        #    value = math.prod([self.template_model.parameters[param]
        #                       for param in rate_parameters])
        #    key = '_'.join(rate_parameters)
        else:
            value = None
            key = get_parameter_key(tkey, 'rate')
        p = self.get_create_parameter(ModelParameter(key, value))
        return p

    def make_model(self):
        for template in self.template_model.templates:
            if isinstance(template, (NaturalConversion, NaturalProduction, NaturalDegradation)):
                if isinstance(template, (NaturalConversion, NaturalDegradation)):
                    s = self.assemble_variable(template.subject,
                                               self.template_model.initials)
                    consumed = (s,)
                else:
                    consumed = tuple()
                if isinstance(template, (NaturalConversion, NaturalProduction)):
                    o = self.assemble_variable(template.outcome,
                                               self.template_model.initials)
                    produced = (o,)
                else:
                    produced = tuple()

                consumed_key = tuple(s.key for s in consumed) \
                    if len(consumed) != 1 else consumed[0].key
                produced_key = tuple(o.key for o in produced) \
                    if len(produced) != 1 else produced[0].key
                tkey = get_transition_key((consumed_key, produced_key),
                                          template.type)
                p = self.assemble_parameter(template, tkey)
                self.get_create_transition(Transition(
                    tkey,
                    consumed=consumed,
                    produced=produced,
                    control=tuple(),
                    rate=p,
                    template_type=template.type,
                ))
            elif isinstance(template, (ControlledConversion, GroupedControlledConversion)):
                s = self.assemble_variable(template.subject,
                                           self.template_model.initials)
                o = self.assemble_variable(template.outcome,
                                           self.template_model.initials)

                if isinstance(template, ControlledConversion):
                    c = self.assemble_variable(template.controller,
                                               self.template_model.initials)
                    control = (c,)
                    tkey = get_transition_key((s.key, o.key, c.key), template.type)
                else:
                    control = tuple(
                        self.assemble_variable(controller,
                                               self.template_model.initials)
                        for controller in template.controllers
                    )
                    tkey = get_transition_key((s.key, o.key,
                                               tuple(c.key for c in control)),
                                              template.type)
                p = self.assemble_parameter(template, tkey)

                self.get_create_transition(Transition(
                    tkey,
                    consumed=(s,),
                    produced=(o,),
                    control=control,
                    rate=p,
                    template_type=template.type,
                ))
            elif isinstance(template, GroupedControlledProduction):
                o = self.assemble_variable(template.outcome,
                                           self.template_model.initials)
                control = tuple(
                    self.assemble_variable(controller,
                                           self.template_model.initials)
                    for controller in template.controllers
                )
                tkey = get_transition_key(
                    (o.key, tuple(c.key for c in control)), template.type
                )
                p = self.assemble_parameter(template, tkey)

                self.get_create_transition(Transition(
                    tkey,
                    consumed=tuple(),
                    produced=(o,),
                    control=control,
                    rate=p,
                    template_type=template.type,
                ))
            else:
                if template.__class__ not in UNHANDLED_TYPES:
                    logger.warning("unhandled template type: %s", template.__class__)
                    UNHANDLED_TYPES.add(template.__class__)

    def get_create_parameter(self, parameter):
        if parameter.key not in self.parameters:
            self.parameters[parameter.key] = parameter
        return self.parameters[parameter.key]

    def get_create_transition(self, transition):
        if transition.key not in self.transitions:
            self.transitions[transition.key] = transition
        return self.transitions[transition.key]
