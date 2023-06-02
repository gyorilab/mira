"""This module implements generation into Petri net models which are defined
at https://github.com/DARPA-ASKEM/Model-Representations/tree/main/petrinet.
"""

__all__ = ["AskeNetPetriNetModel", "ModelSpecification"]


import json
import logging
from copy import deepcopy
from typing import Dict, List, Optional

import sympy
from pydantic import BaseModel, Field

from mira.metamodel import expression_to_mathml

from .. import Model

logger = logging.getLogger(__name__)

SCHEMA_VERSION = '0.4'
SCHEMA_URL = ('https://raw.githubusercontent.com/DARPA-ASKEM/'
              'Model-Representations/petrinet_v%s/petrinet/'
              'petrinet_schema.json') % SCHEMA_VERSION


class AskeNetPetriNetModel:
    """A class representing a PetriNet model."""

    def __init__(self, model: Model):
        """Instantiate a petri net model from a generic transition model.

        Parameters
        ----------
        model:
            The pre-compiled transition model
        """
        self.properties = {}
        self.initials = []
        self.rates = []
        self.states = []
        self.transitions = []
        self.parameters = []
        self.metadata = {}
        self.model_name = model.template_model.annotations.name if \
            model.template_model.annotations.name else "Model"
        self.model_description = model.template_model.annotations.description \
            if model.template_model.annotations.description else self.model_name
        vmap = {}
        for key, var in model.variables.items():
            # Use the variable's concept name if possible but fall back
            # on the key otherwise
            vmap[key] = name = var.concept.name or str(key)
            # State structure
            # {
            #   'id': str,
            #   'name': str,
            #   'grounding': {identifiers, context},
            # }
            states_dict = {
                'id': name,
                'name': name,
                'grounding': {
                    'identifiers': {k: v for k, v in
                                    var.concept.identifiers.items()
                                    if k != 'biomodels.species'},
                    'context': var.concept.context,
                },
            }
            self.states.append(states_dict)
            # 'initial' object structure
            # {
            #   'target': str,  # refers to a state id above
            #   'expression': str,
            #   'expression_mathml': str,
            # }
            initial = var.data.get('initial_value')
            if initial is not None:
                if isinstance(initial, float):
                    initial = sympy.parse_expr(str(initial))
                initial_data = {
                    'target': name,
                    'expression': str(initial),
                    'expression_mathml': expression_to_mathml(initial)
                }
                self.initials.append(initial_data)

        # Transition structure
        # {
        #   "id": "t1",
        #   "input": ["s1", "s2"],
        #   "output": ["s3", "s4"],
        #   "grounding": {identifiers, context},
        #   "properties": {...}, keys: name, grounding > {identifiers, context}
        # }
        # Rate structure:
        # {
        #   target: string,  # refers to a transition id above
        #   expression: string,
        #   expression_mathml
        # }
        for idx, transition in enumerate(model.transitions.values()):
            tid = f"t{idx + 1}"
            # fixme: get grounding for transition
            transition_dict = {"id": tid}

            inputs = []
            outputs = []
            for c in transition.control:
                inputs.append(vmap[c.key])
                outputs.append(vmap[c.key])
            for c in transition.consumed:
                inputs.append(vmap[c.key])
            for p in transition.produced:
                outputs.append(vmap[p.key])

            transition_dict['input'] = inputs
            transition_dict['output'] = outputs

            # Include rate law
            if transition.template.rate_law:
                rate_law = transition.template.rate_law.args[0]
                self.rates.append({
                    'target': tid,
                    'expression': sanitize_parameter_name(str(rate_law)),
                    'expression_mathml': sanitize_parameter_name(
                        expression_to_mathml(rate_law))
                })

            transition_dict['properties'] = {
                'name': tid,
            }

            self.transitions.append(transition_dict)

        for key, param in model.parameters.items():
            if param.placeholder:
                continue
            param_dict = {
                'id': sanitize_parameter_name(str(key)),
            }
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

    def to_json(self, name=None, description=None, model_version=None):
        """Return a JSON dict structure of the Petri net model."""
        return {
            'name': name or self.model_name,
            'schema': SCHEMA_URL,
            'description': description or self.model_description,
            'model_version': model_version or '0.1',
            'properties': self.properties,
            'model': {
                'states': self.states,
                'transitions': self.transitions,
            },
            'semantics': {'ode': {
                'rates': self.rates,
                'initials': self.initials,
                'parameters': self.parameters
            }},
            'metadata': self.metadata,
        }

    def to_pydantic(self, name=None, description=None, model_version=None) -> "ModelSpecification":
        return ModelSpecification(
            name=name or self.model_name,
            schema=SCHEMA_URL,
            description=description or self.model_description,
            model_version=model_version or '0.1',
            properties=self.properties,
            model=PetriModel(
                states=[State.parse_obj(s) for s in self.states],
                transitions=[Transition.parse_obj(t) for t in self.transitions],
            ),
            semantics=Ode(ode=OdeSemantics(
                rates=[Rate.parse_obj(r) for r in self.rates],
                initials=[Initial.parse_obj(i) for i in self.initials],
                parameters=[Parameter.parse_obj(p) for p in self.parameters],
            )),
            metadata=self.metadata,
        )

    def to_json_str(self, **kwargs):
        """Return a JSON string representation of the Petri net model."""
        return json.dumps(self.to_json(), **kwargs)

    def to_json_file(self, fname, name=None, description=None,
                     model_version=None, **kwargs):
        """Write the Petri net model to a JSON file

        Parameters
        ----------
        fname : str
            The file name to write to.
        name : str, optional
            The name of the model.
        description : str, optional
            A description of the model.
        model_version : str, optional
            The version of the model.
        kwargs :
            Additional keyword arguments to pass to :func:`json.dump`.
        """
        js = self.to_json(name=name, description=description,
                          model_version=model_version)
        with open(fname, 'w') as fh:
            json.dump(js, fh, **kwargs)


class Initial(BaseModel):
    target: str
    expression: str
    expression_mathml: str


class TransitionProperties(BaseModel):
    name: Optional[str]
    grounding: Optional[Dict]


class Rate(BaseModel):
    target: str
    expression: str
    expression_mathml: str


class Distribution(BaseModel):
    type: str
    parameters: Dict


class State(BaseModel):
    id: str
    name: Optional[str] = None
    grounding: Optional[Dict]


class Transition(BaseModel):
    id: str
    input: List[str]
    output: List[str]
    grounding: Optional[Dict]
    properties: Optional[TransitionProperties]


class Parameter(BaseModel):
    id: str
    description: Optional[str] = None
    value: Optional[float] = None
    grounding: Optional[Dict]
    distribution: Optional[Distribution] = None

    @classmethod
    def from_dict(cls, d):
        d = deepcopy(d)
        d['id'] = str(d['id'])
        return cls.parse_obj(d)


class PetriModel(BaseModel):
    states: List[State]
    transitions: List[Transition]


class OdeSemantics(BaseModel):
    rates: List[Rate]
    initials: List[Initial]
    parameters: List[Parameter]


class Ode(BaseModel):
    ode: Optional[OdeSemantics]


class ModelSpecification(BaseModel):
    name: str
    schema_url: str = Field(..., alias='schema')
    description: str
    model_version: str
    properties: Optional[Dict]
    model: PetriModel
    semantics: Optional[Ode]
    metadata: Optional[Dict]


def sanitize_parameter_name(pname):
    # This is to revert a sympy representation issue
    return pname.replace('XXlambdaXX', 'lambda')
