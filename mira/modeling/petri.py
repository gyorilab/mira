"""This module implements generation into Petri net models which are defined
through a set of states, transitions, and the input and output connections
between them.

Once the model is created, it can be exported into JSON following the
conventions in https://github.com/AlgebraicJulia/ASKEM-demos/tree/master/data.
"""

__all__ = ["PetriNetModel"]

import json

from . import Model


class PetriNetModel:
    """A class representing a PetriNet model."""
    def __init__(self, model: Model):
        self.states = []
        self.transitions = []
        self.inputs = []
        self.outputs = []
        self.vmap = {variable.key: (idx + 1) for idx, variable
                     in enumerate(model.variables.values())}
        for key, var in model.variables.items():
            # Use the variable's concept name if possible but fall back
            # on the key otherwise
            name = var.data.get('name') or str(key)
            ids = str(var.data.get('identifiers', '')) or None
            context = str(var.data.get('context', '')) or None
            self.states.append({'sname': name,
                                'mira_ids': ids,
                                'mira_context': context})

        for idx, transition in enumerate(model.transitions.values()):
            self.transitions.append(
                {'tname': f"t{idx + 1}",
                 'template_type': transition.template_type,
                 'parameter_name': sanitize_parameter_name(
                     str(transition.rate.key)),
                 'parameter_value': transition.rate.value}
            )
            for c in transition.control:
                self.inputs.append({'is': self.vmap[c.key],
                                    'it': idx + 1})
                self.outputs.append({'os': self.vmap[c.key],
                                     'ot': idx + 1})
            for c in transition.consumed:
                self.inputs.append({'is': self.vmap[c.key],
                                    'it': idx + 1})
            for p in transition.produced:
                self.outputs.append({'os': self.vmap[p.key],
                                     'ot': idx + 1})

    def to_json(self):
        """Return a JSON dict structure of the Petri net model."""
        return {
            'S': self.states,
            'T': self.transitions,
            'I': self.inputs,
            'O': self.outputs
        }

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
