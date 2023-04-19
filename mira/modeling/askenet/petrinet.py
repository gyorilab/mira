"""This module implements generation into Petri net models which are defined
at https://github.com/DARPA-ASKEM/Model-Representations/tree/main/petrinet.
"""

__all__ = ["AskeNetPetriNetModel"]


SCHEMA_VERSION = '0.1'
SCHEMA_URL = ('https://raw.githubusercontent.com/DARPA-ASKEM/'
              'Model-Representations/petrinet_v%s/petrinet/'
              'petrinet_schema.json') % SCHEMA_VERSION

import json
from typing import Dict, List, Optional

from pydantic import BaseModel

from .. import Model
from mira.metamodel import expression_to_mathml


class Initial(BaseModel):
    expression: str
    expression_mathml: str


class TransitionProperties(BaseModel):
    name: str
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
    initial: Initial


class Transition(BaseModel):
    id: str
    input: List[str]
    output: List[str]
    properties: Optional[TransitionProperties]


class Parameter(BaseModel):
    id: str
    description: str
    value: float
    distribution: Distribution


class PetriModel(BaseModel):
    states: List[State]
    transitions: List[Transition]
    parameters: List[Parameter]


class ModelSpecification(BaseModel):
    name: str
    schema: str
    description: str
    model_version: str
    properties: Optional[Dict]
    model: PetriModel


class PetriNetModel:
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
        #self.observables = []
        self.vmap = {}
        for key, var in model.variables.items():
            # Use the variable's concept name if possible but fall back
            # on the key otherwise
            name = var.data.get('name') or str(key)
            self.vmap[key] = name
            ids = str(var.data.get('identifiers', '')) or None
            context = str(var.data.get('context', '')) or None
            grounding = {}
            if ids is not None:
                grounding['identifiers'] = ids
            if context is not None:
                grounding['context'] = context
            state_data = {
                'id': name,
                'name': name,
                'grounding': grounding,
            }
            initial = var.data.get('initial_value')
            if initial is not None:
                state_data['initial'] = {
                    'expression': str(initial),
                    'expression_mathml': expression_to_mathml(initial),
                }
            self.states.append(state_data)

        for idx, transition in enumerate(model.transitions.values()):
            transition_dict = {'id': f"t{idx + 1}"}

            inputs = []
            outputs = []
            for c in transition.control:
                inputs.append(self.vmap[c.key])
                outputs.append(self.vmap[c.key])
            for c in transition.consumed:
                inputs.append(self.vmap[c.key])
            for p in transition.produced:
                outputs.append(self.vmap[p.key])

            transition_dict['input'] = inputs
            transition_dict['output'] = outputs

            # Include rate law
            if transition.template.rate_law:
                rate_law = transition.template.rate_law.args[0]
                transition_dict['properties'] = {
                    'rate': {
                        'expression': str(rate_law),
                        'expression_mathml': expression_to_mathml(rate_law),
                    }
                }

            self.transitions.append(transition_dict)


    def to_json(self):
        """Return a JSON dict structure of the Petri net model."""
        return {
            'S': self.states,
            'T': self.transitions,
            'I': self.inputs,
            'O': self.outputs,
            #'B': self.observables,
        }

    def to_pydantic(self):
        return ModelSpecification(**self.to_json())

    def to_json_str(self):
        """Return a JSON string representation of the Petri net model."""
        return json.dumps(self.to_json())

    def to_json_file(self, fname, **kwargs):
        """Write the Petri net model to a JSON file."""
        js = self.to_json()
        with open(fname, 'w') as fh:
            json.dump(js, fh, **kwargs)


def sanitize_parameter_name(pname):
    # This is to revert a sympy representation issue
    return pname.replace('XXlambdaXX', 'lambda')



def AskeNetPetriNetModel:
