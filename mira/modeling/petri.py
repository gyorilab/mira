__all__ = ["PetriNetModel"]

import json

from . import Model


class PetriNetModel:
    def __init__(self, model: Model):
        self.states = []
        self.transitions  = []
        self.inputs = []
        self.outputs = []
        self.vmap = {variable.key: (idx + 1) for idx, variable
                     in enumerate(model.variables.values())}
        for k, v in model.variables.items():
            self.states.append({'sname': str(k)})

        for idx, transition in enumerate(model.transitions.values()):
            self.transitions.append({'tname': str(transition.key)})
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
        return {
            'S': self.states,
            'T': self.transitions,
            'I': self.inputs,
            'O': self.outputs
        }

    def to_json_str(self):
        return json.dumps(self.to_json())

    def to_json_file(self, fname, **kwargs):
        js = self.to_json()
        with open(fname, 'w') as fh:
            json.dumps(fname, js, **kwargs)
