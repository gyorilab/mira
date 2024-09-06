"""This module implements generation into Petri net models which are defined
at https://github.com/DARPA-ASKEM/Model-Representations/tree/main/regnet.
"""

__all__ = ["AMRRegNetModel", "ModelSpecification",
           "template_model_to_regnet_json"]

import json
import logging
from copy import deepcopy
from collections import defaultdict
from typing import Dict, List, Optional, Union

import sympy
from pydantic import BaseModel, Field

from mira.metamodel import *

from .. import Model, is_production, is_conversion
from .utils import add_metadata_annotations

logger = logging.getLogger(__name__)

SCHEMA_VERSION = '0.2'
SCHEMA_URL = ('https://raw.githubusercontent.com/DARPA-ASKEM/'
              'Model-Representations/regnet_v%s/regnet/'
              'regnet_schema.json') % SCHEMA_VERSION


class AMRRegNetModel:
    """A class representing a PetriNet model."""

    def __init__(self, model: Model):
        """Instantiate a regnet model from a generic transition model.

        Parameters
        ----------
        model:
            The pre-compiled transition model
        """
        self.states = []
        self.transitions = []
        self.parameters = []
        self.model_name = model.template_model.annotations.name if \
            model.template_model.annotations and \
            model.template_model.annotations.name else "Model"
        self.model_description = model.template_model.annotations.description \
            if model.template_model.annotations and \
               model.template_model.annotations.description else self.model_name

        self.rates = []
        self.observables = []
        self.time = None

        self.metadata = {}
        self._states_by_id = {}

        vmap = {}
        for key, var in model.variables.items():
            # Use the variable's concept name if possible but fall back
            # on the key otherwise
            vmap[key] = name = var.concept.name or str(key)
            state_data = {
                'id': name,
                'name': name,
                'grounding': {
                    'identifiers': {k: v for k, v in
                                    var.concept.identifiers.items()
                                    if k != 'biomodels.species'},
                    'context': var.concept.context,
                },
            }
            initial = var.data.get('expression')
            if initial is not None:
                # Here, initial is a SympyExprStr, and if its
                # value is a float, we export it as a float,
                # otherwise we export it as a string
                try:
                    initial_float = float(initial.args[0])
                    state_data['initial'] = initial_float
                except TypeError:
                    state_data['initial'] = str(initial)
            self.states.append(state_data)
            self._states_by_id[name] = state_data

        edge_id = 1
        # It's possible that something is naturally degraded/replicated
        # by multiple transitions so we need to collect and aggregate rates
        intrinsic_by_var = defaultdict(list)
        for transition in model.transitions.values():
            # Regnets cannot represent conversions (only
            # production/degradation) so we skip these
            if is_conversion(transition.template):
                continue

            # Now let's look for intrinsic growth/decay which is represented
            # at the vertex level in regnets
            natdeg = isinstance(transition.template, NaturalDegradation)
            natrep = isinstance(transition.template, NaturalReplication)
            contprod = isinstance(transition.template, ControlledProduction)

            # Natural degradation corresponds to an inherent negative
            # sign on the state so we have special handling for it
            if natdeg or natrep or (contprod and (transition.control[0].key
                                                  == transition.produced[0].key)):
                if natdeg:
                    var = vmap[transition.consumed[0].key]
                    sign = False
                elif natrep:
                    var = vmap[transition.produced[0].key]
                    sign = True
                elif contprod:
                    var = vmap[transition.produced[0].key]
                    sign = True

                state_for_var = self._states_by_id.get(var)
                if transition.template.rate_law:
                    pnames = transition.template.get_parameter_names()
                    # We just choose an arbitrary one deterministically
                    rate_const = sorted(pnames)[0] if pnames else None
                    if state_for_var:
                        state_for_var['rate_constant'] = rate_const
                if state_for_var:
                    state_for_var['sign'] = sign

                if transition.template.rate_law:
                    rate_law = transition.template.rate_law.args[0]
                    intrinsic_by_var[var].append(rate_law)
            # Beyond these, we can assume that the transition is a
            # form of replication or degradation corresponding to
            # a regular transition in the regnet framework
            # Possibilities are:
            # - ControlledReplication / GroupedControlledProduction
            # - ControlledDegradation / GroupedControlledDegradation
            # - ControlledProduction if the control and produced concept are not the same
            else:
                # If we have multiple controls then the thing that replicates
                # is both a control and a produced variable.
                if len(transition.control) > 1:
                    # GroupedControlledProduction
                    if is_production(transition.template) or is_replication(
                        transition.template
                    ):
                        indep_ctrl = {c.key for c in transition.control} - {
                            transition.produced[0].key
                        }
                        # There is one corner case where both controllers are also
                        # the same as the produced variable, in which case.
                        if not indep_ctrl:
                            indep_ctrl = {transition.produced[0].key}

                        for index, controller in enumerate(indep_ctrl):
                            self.create_edge(
                                transition,
                                vmap[controller],
                                vmap[transition.produced[0].key],
                                edge_id,
                                False if index == 0 else True
                            )

                            edge_id += 1
                    else:
                        # GroupedControlledDegradation
                        indep_ctrl = {c.key for c in transition.control} - {
                            transition.consumed[0].key
                        }
                        # There is one corner case where both controllers are also
                        # the same as the consumed variable, in which case.
                        if not indep_ctrl:
                            indep_ctrl = {transition.consumed[0].key}

                        for index, controller in enumerate(indep_ctrl):
                            self.create_edge(
                                transition,
                                vmap[controller],
                                vmap[transition.consumed[0].key],
                                edge_id,
                                False if index == 0 else True
                            )

                            edge_id += 1
                else:
                    # ControlledProduction if produced and controller are not the same
                    # ControlledDegradation
                    target = vmap[
                        transition.consumed[0].key
                        if transition.consumed
                        else transition.produced[0].key
                    ]
                    self.create_edge(
                        transition,
                        vmap[transition.control[0].key],
                        target,
                        edge_id,
                        False
                    )
                    edge_id += 1

        for var, rates in intrinsic_by_var.items():
            rate_law = sum(rates)
            self.rates.append({
                'target': var,
                'expression': str(rate_law),
                'expression_mathml': expression_to_mathml(rate_law)
            })

        for key, param in model.parameters.items():
            if param.placeholder:
                continue
            param_dict = {'id': str(key)}
            if param.value is not None:
                param_dict['value'] = param.value
            if not param.distribution:
                pass
            elif param.distribution.type is None:
                logger.warning("can not add distribution without type: %s", param.distribution)
            else:
                param_dict['distribution'] = {
                    'type': param.distribution.type,
                    'parameters': param.distribution.parameters,
                }
            self.parameters.append(param_dict)

        for key, observable in model.observables.items():
            display_name = observable.observable.display_name \
                if observable.observable.display_name \
                else observable.observable.name
            obs_data = {
                'id': observable.observable.name,
                'name': display_name,
                'expression': str(observable.observable.expression),
                'expression_mathml': expression_to_mathml(
                    observable.observable.expression.args[0]),
            }
            self.observables.append(obs_data)

        if model.template_model.time:
            self.time = {'id': model.template_model.time.name}
            if model.template_model.time.units:
                self.time['units'] = {
                    'expression': str(model.template_model.time.units.expression),
                    'expression_mathml': expression_to_mathml(
                        model.template_model.time.units.expression.args[0]),
                }
        else:
            self.time = None
        add_metadata_annotations(self.metadata, model)

    def create_edge(self, transition, source, target, edge_id, duplicate):
        """Create and append a transition dictionary to the list of transitions

        Parameters
        ----------
        transition : Transition
            The Transition object
        source : str
            The name of the source of the transition
        target : str
            The name of the target of the transition
        edge_id : int
            The id to assign to the transition
        duplicate : bool
            A boolean that tells us whether the transition we are processing has already been
            processed at least once. This is for the purpose of not adding duplicate rate laws
            to the output amr.
        """
        tid = f"t{edge_id}"
        transition_dict = {"id": tid}
        transition_dict["source"] = source
        transition_dict["target"] = target
        transition_dict["sign"] = is_production(
            transition.template
        ) or is_replication(transition.template)

        #
        if transition.template.rate_law:
            # If we are processing a duplicate rate, set the rate to 0
            rate_law = transition.template.rate_law.args[0] if not duplicate \
                else safe_parse_expr('0')
            pnames = transition.template.get_parameter_names()
            # We just choose an arbitrary one deterministically
            rate_const = sorted(pnames)[0] if pnames else None

            transition_dict["properties"] = {
                "name": tid,
                "rate_constant": rate_const,
            }
            self.rates.append(
                {
                    "target": tid,
                    "expression": str(rate_law),
                    "expression_mathml": expression_to_mathml(rate_law),
                }
            )

        self.transitions.append(transition_dict)

    def to_json(
        self,
        name: str = None,
        description: str = None,
        model_version: str = None
    ):
        """Return a JSON dict structure of the Petri net model.

        Parameters
        ----------
        name :
            The name of the model. Defaults to the model name of the original
            template model of the input Model instance, or "Model" if no name
            is available.
        description :
            The description of the model. Defaults to the description of the
            original template model of the input Model instance, or the model
            name if no description is available.
        model_version :
            The version of the model. Defaults to 0.1

        Returns
        -------
        : JSON
            A JSON representation of the Petri net model.
        """
        return {
            'header': {
                'name': name or self.model_name,
                'schema': SCHEMA_URL,
                'schema_name': 'regnet',
                'description': description or self.model_description,
                'model_version': model_version or '0.1',
            },
            'model': {
                'vertices': self.states,
                'edges': self.transitions,
                'parameters': self.parameters,
            },
            'semantics': {'ode': {
                'rates': self.rates,
                'observables': self.observables,
                'time': self.time if self.time else {'id': 't'}
            }},
            'metadata': self.metadata,
        }

    def to_pydantic(
        self,
        name: str = None,
        description: str = None,
        model_version: str = None
    ) -> "ModelSpecification":
        """Return a Pydantic model specification of the Petri net model.

        Parameters
        ----------
        name :
            The name of the model. Defaults to the model name of the original
            template model of the input Model instance, or "Model" if no name
            is available.
        description :
            The description of the model. Defaults to the description of the
            original template model of the input Model instance, or the model
            name if no description is available.
        model_version :
            The version of the model. Defaults to 0.1

        Returns
        -------
        :
            A Pydantic model specification of the Petri net model.
        """
        return ModelSpecification(
            header=Header(
                name=name or self.model_name,
                schema=SCHEMA_URL,
                schema_name='regnet',
                description=description or self.model_description,
                model_version=model_version or '0.1',
            ),
            model=RegNetModel(
                vertices=[State.parse_obj(s) for s in self.states],
                edges=[Transition.parse_obj(t) for t in self.transitions],
                parameters=[Parameter.from_dict(p) for p in self.parameters],
            ),
            semantics=Ode(
                ode=OdeSemantics(
                    rates=[Rate.parse_obj(r) for r in self.rates],
                    observables=[Observable.parse_obj(o) for o in self.observables],
                    time=Time.parse_obj(self.time) if self.time else Time(id='t')
                )
            ),
            metadata=self.metadata,
        )

    def to_json_str(self, **kwargs):
        """Return a JSON string representation of the Petri net model.

        Parameters
        ----------
        **kwargs :
            Keyword arguments to be passed to json.dumps

        Returns
        -------
        :
            A JSON string representation of the Petri net model.
        """
        return json.dumps(self.to_json(), **kwargs)

    def to_json_file(
        self,
        fname: str,
        name: str = None,
        description: str = None,
        model_version: str = None,
        **kwargs
    ):
        """Write the Petri net model to a JSON file.

        Parameters
        ----------
        fname :
            The file name to write to.
        name :
            The name of the model. Defaults to the model name of the original
            template model of the input Model instance, or "Model" if no name
            is available.
        description :
            The description of the model. Defaults to the description of the
            original template model of the input Model instance, or the model
            name if no description is available.
        model_version :
            The version of the model. Defaults to 0.1
        **kwargs :
            Keyword arguments to be passed to json.dump
        """
        js = self.to_json(name=name, description=description,
                          model_version=model_version)
        with open(fname, 'w') as fh:
            json.dump(js, fh, **kwargs)


def template_model_to_regnet_json(tm: TemplateModel):
    """Convert a template model to a RegNet JSON dict.

    Parameters
    ----------
    tm :
        The template model to convert.

    Returns
    -------
    A JSON dict representing the RegNet model.
    """
    return AMRRegNetModel(Model(tm)).to_json()


class Initial(BaseModel):
    expression: Union[str, float]
    expression_mathml: str


class TransitionProperties(BaseModel):
    name: Optional[str] = None
    grounding: Optional[Dict] = None
    rate: Optional[Dict] = None


class Rate(BaseModel):
    expression: str
    expression_mathml: str


class Distribution(BaseModel):
    type: str
    parameters: Dict


class State(BaseModel):
    id: str
    name: str
    initial: Optional[Initial] = None


class Transition(BaseModel):
    id: str
    input: List[str]
    output: List[str]
    properties: Optional[TransitionProperties] = None


class Parameter(BaseModel):
    id: str
    value: Optional[float] = None
    description: Optional[str] = None
    distribution: Optional[Distribution] = None

    @classmethod
    def from_dict(cls, d):
        d = deepcopy(d)
        d['id'] = str(d['id'])
        return cls.parse_obj(d)


class RegNetModel(BaseModel):
    vertices: List[State]
    edges: List[Transition]
    parameters: List[Parameter]


class Header(BaseModel):
    name: str
    schema_name: str
    schema_url: str = Field(..., alias='schema')
    description: str
    model_version: str


class OdeSemantics(BaseModel):
    rates: List[Rate]
    time: Optional[Time] = None
    observables: List[Observable]


class Ode(BaseModel):
    ode: Optional[OdeSemantics] = None


class ModelSpecification(BaseModel):
    """A Pydantic model specification of the model."""
    header: Header
    properties: Optional[Dict] = None
    model: RegNetModel
    semantics: Optional[Ode] = None
    metadata: Optional[Dict] = None
