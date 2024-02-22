"""Modeling module for MIRA.

The top level contains the Model class, toghether with the Variable,
Transition, and ModelParameter classes, used to represent a Model.
"""
__all__ = ["Model", "Transition", "Variable", "ModelParameter"]

import logging
from typing import Dict, Hashable, Mapping, Optional

from mira.metamodel import *

logger = logging.getLogger(__name__)


# TODO: Consider using dataclasses


class Transition:
    """A transition between two concepts, with a rate law.

    Attributes
    ----------
    key : tuple[str]
        A tuple of the form (consumed, produced, control, rate)
    consumed : tuple[Variable]
        The variables consumed by the transition
    produced : tuple[Variable]
        The variables produced by the transition
    control : tuple[Variable]
        The variables that control the transition
    """
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
    """A variable representation of a concept in Model

    Attributes
    ----------
    key : tuple[str, ...]
        A tuple of strings representing the concept name, grounding, and context
    data : dict
        A dictionary of data about the variable
    concept : Concept
        The concept associated with the variable
    """
    def __init__(self, key, data, concept: Concept):
        self.key = key
        self.data = data
        self.concept = concept


class ModelParameter:
    """A parameter for a model.

    Attributes
    ----------
    key : tuple[str, ...]
        A tuple of strings representing the transition key and the parameter type
    display_name : str
        The display name of the parameter. (optional)
    description : str
        A description of the parameter. (optional)
    value : float
        The value of the parameter. (optional)
    distribution : str
        The distribution of the parameter. (optional)
    placeholder : bool
        Whether the parameter is a placeholder. (optional)
    concept : Concept
        The concept associated with the parameter. (optional)
    """
    def __init__(self, key, display_name=None, description=None, value=None,
                 distribution=None, placeholder=None, concept=None):
        self.key = key
        self.display_name = display_name
        self.description = description
        self.value = value
        self.distribution = distribution
        self.placeholder = placeholder
        self.concept = concept


class ModelObservable:
    """An observable for a model.

    Attributes
    ----------
    observable : Observable
        The observable
    parameters : tuple[str, ...]
        The parameters of the observable
    """
    def __init__(self, observable, parameters):
        self.observable = observable
        self.parameters = parameters


def get_transition_key(concept_keys, action):
    return concept_keys + (action,)


def get_parameter_key(transition_key, action):
    return transition_key + (action,)


UNHANDLED_TYPES = set()


class Model:
    """A model representation generated from a template model.

    Attributes
    ----------
    template_model : TemplateModel
        The template model used to generate the model
    variables : dict[Hashable, Variable]
        A dictionary mapping from variable keys to variables
    parameters : dict[Hashable, ModelParameter]
        A dictionary mapping from parameter keys to parameters
    transitions : dict[Hashable, Transition]
        A dictionary mapping from transition keys to transitions
    observables : dict[Hashable, ModelObservable]
        A dictionary mapping from observable keys to observables
    """
    def __init__(self, template_model: TemplateModel):
        """

        Parameters
        ----------
        template_model :
            A template model to generate a model from
        """
        self.template_model = template_model
        self.variables: Dict[Hashable, Variable] = {}
        self.parameters: Dict[Hashable, ModelParameter] = {}
        self.transitions: Dict[Hashable, Transition] = {}
        self.observables: Dict[Hashable, ModelObservable] = {}
        self.make_model()

    def assemble_variable(
            self, concept: Concept, initials: Optional[Mapping[str, Initial]] = None,
    ) -> Variable:
        """Assemble a variable from a concept and optional dictionary of
        initial values.

        Parameters
        ----------
        concept :
            The concept for the variable
        initials :
            A dictionary mapping from names of concepts to objects
            representing their initial values

        Returns
        -------
        :
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

        # We don't assume that the initial dict key is the same as the
        # name of the given concept the initial applies to, so we check
        # concept name match instead of key match.
        initial_expr = None
        if initials:
            for k, v in initials.items():
                if v.concept.name == concept.name:
                    initial_expr = v.expression

        data = {
            'name': concept.name,
            'identifiers': grounding_key,
            'context': context_key,
            'expression': initial_expr
        }
        var = Variable(key, data=data, concept=concept)
        self.variables[key] = var
        return var

    def assemble_parameter(self, template: Template, tkey) -> ModelParameter:
        """Assemble a parameter from a template and a transition key.

        Parameters
        ----------
        template :
            The template to assemble a parameter from
        tkey : tuple[str, ...]
            The transition key to assemble a parameter from

        Returns
        -------
        :
            A model parameter
        """
        rate_parameters = sorted(
            self.template_model.get_parameters_from_rate_law(template.rate_law))

        if rate_parameters:
            model_parameters = []
            for key in rate_parameters:
                param = self.template_model.parameters[key]
                model_parameters.append(
                    self.get_create_parameter(
                        ModelParameter(key, value=param.value, distribution=param.distribution,
                                       description=param.description,
                                       display_name=param.display_name,
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
        """Initialize the model"""
        for name, observable in self.template_model.observables.items():
            params = sorted(
                observable.get_parameter_names(self.template_model.parameters))
            self.observables[observable.name] = \
                ModelObservable(observable, params)
            for key in params:
                value = self.template_model.parameters[key].value
                distribution = self.template_model.parameters[key].distribution
                display_name = self.template_model.parameters[key].display_name
                description = self.template_model.parameters[key].description
                self.get_create_parameter(
                    ModelParameter(key, display_name=display_name, description=description,
                                   distribution=distribution,
                                   value=value,
                                   placeholder=False))

        for template in self.template_model.templates:
            if isinstance(template, StaticConcept):
                self.assemble_variable(template.subject,
                                       self.template_model.initials)
                continue

            # Handle subjects
            if has_subject(template):
                s = self.assemble_variable(template.subject,
                                           self.template_model.initials)
                consumed, consumed_key = (s,), s.key
                if is_replication(template):
                    produced, produced_key = (s,), s.key
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
            elif not is_replication(template):
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

        for key, parameter in self.template_model.parameters.items():
            if key not in self.parameters:
                value = self.template_model.parameters[key].value
                distribution = self.template_model.parameters[key].distribution
                display_name = self.template_model.parameters[key].display_name
                description = self.template_model.parameters[key].description
                self.get_create_parameter(
                    ModelParameter(key, display_name=display_name, description=description,
                                   distribution=distribution,
                                   value=value,
                                   placeholder=False))

    def get_create_parameter(self, parameter: ModelParameter) -> ModelParameter:
        if parameter.key not in self.parameters:
            self.parameters[parameter.key] = parameter
        return self.parameters[parameter.key]

    def get_create_transition(self, transition: Transition) -> Transition:
        if transition.key not in self.transitions:
            self.transitions[transition.key] = transition
        return self.transitions[transition.key]

