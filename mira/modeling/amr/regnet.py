"""This module implements generation into Petri net models which are defined
at https://github.com/DARPA-ASKEM/Model-Representations/tree/main/petrinet.
"""

__all__ = ["AMRRegNetModel", "ModelSpecification"]


import json
import logging
from copy import deepcopy
from typing import Dict, List, Optional

import sympy
from pydantic import BaseModel, Field

from mira.metamodel import *

from .. import Model, is_production
from .utils import add_metadata_annotations

logger = logging.getLogger(__name__)

SCHEMA_VERSION = '0.2'
SCHEMA_URL = ('https://raw.githubusercontent.com/DARPA-ASKEM/'
              'Model-Representations/regnet_v%s/regnet/'
              'regnet_schema.json') % SCHEMA_VERSION


class AMRRegNetModel:
    """A class representing a PetriNet model."""

    def __init__(self, model: Model):
        """Instantiate a petri net model from a generic transition model.

        Parameters
        ----------
        model:
            The pre-compiled transition model
        """
        self.states = []
        self.transitions = []
        self.parameters = []
        self.model_name = model.template_model.annotations.name if \
            model.template_model.annotations.name else "Model"
        self.model_description = model.template_model.annotations.description \
            if model.template_model.annotations.description else self.model_name
        self.metadata = {}
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
            initial = var.data.get('initial_value')
            if initial is not None:
                if isinstance(initial, float):
                    initial = safe_parse_expr(str(initial))
                state_data['initial'] = str(initial)
            self.states.append(state_data)

        for idx, transition in enumerate(model.transitions.values()):
            if isinstance(transition.template, NaturalDegradation):
                var = vmap[transition.consumed[0].key]
                if transition.template.rate_law:
                    pnames = transition.template.get_parameter_names()
                    if len(pnames) == 1:
                        rate_const = list(pnames)[0]
                    else:
                        rate_const = float(list(pnames)[0])
                    for state in self.states:
                        if state['id'] == var:
                            state['rate_constant'] = rate_const
                            state['sign'] = False
                else:
                    state['sign'] = False
                continue
            elif isinstance(transition.template, ControlledProduction):
                var = vmap[transition.produced[0].key]
                if transition.template.rate_law:
                    pnames = transition.template.get_parameter_names()
                    if len(pnames) == 1:
                        rate_const = list(pnames)[0]
                    else:
                        rate_const = float(list(pnames)[0])
                    for state in self.states:
                        if state['id'] == var:
                            state['rate_constant'] = rate_const
                            state['sign'] = True
                else:
                    state['sign'] = True
                continue
            tid = f"t{idx + 1}"
            transition_dict = {'id': tid}

            inputs = []
            outputs = []
            for c in transition.control:
                inputs.append(vmap[c.key])
                outputs.append(vmap[c.key])
            for c in transition.consumed:
                inputs.append(vmap[c.key])
            for p in transition.produced:
                outputs.append(vmap[p.key])

            transition_dict['source'] = inputs[1]
            transition_dict['target'] = outputs[0]
            transition_dict['sign'] = \
                True if is_production(transition.template) else False

            # Include rate law
            if transition.template.rate_law:
                pnames = transition.template.get_parameter_names()
                if len(pnames) == 1:
                    rate_const = list(pnames)[0]
                else:
                    rate_const = float(list(pnames)[0])

                transition_dict['properties'] = {
                    'name': tid,
                    'rate_constant': rate_const,
                }

            self.transitions.append(transition_dict)

        for key, param in model.parameters.items():
            param_dict = {'id': str(key)}
            if param.value:
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

        add_metadata_annotations(self.metadata, model)

    def to_json(self, name=None, description=None, model_version=None):
        """Return a JSON dict structure of the Petri net model."""
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
            'metadata': self.metadata,
        }

    def to_pydantic(self, name=None, description=None, model_version=None) -> "ModelSpecification":
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
        )

    def to_json_str(self, **kwargs):
        """Return a JSON string representation of the Petri net model."""
        return json.dumps(self.to_json(), **kwargs)

    def to_json_file(self, fname, name=None, description=None,
                     model_version=None, **kwargs):
        """Write the Petri net model to a JSON file."""
        js = self.to_json(name=name, description=description,
                          model_version=model_version)
        with open(fname, 'w') as fh:
            json.dump(js, fh, **kwargs)


class Initial(BaseModel):
    expression: str
    expression_mathml: str


class TransitionProperties(BaseModel):
    name: Optional[str]
    grounding: Optional[Dict]
    rate: Optional[Dict]


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
    properties: Optional[TransitionProperties]


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


class ModelSpecification(BaseModel):
    header: Header
    properties: Optional[Dict]
    model: RegNetModel
