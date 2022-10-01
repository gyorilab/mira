"""This module can generate a bilayer structure from a MIRA transition
model."""
import json

from . import Model


class BilayerModel:
    """Class to generate a bilayer model from a transition model."""
    def __init__(self, model: Model):
        self.model = model
        self.bilayer = self.make_bilayer(self.model)

    @staticmethod
    def make_bilayer(model):
        """Generate a bilayer structure and return as a JSON dict."""
        vars = {variable.key: idx + 1
                for idx, variable in enumerate(model.variables.values())}
        boxes = []
        win = []
        wa = []
        wn = []
        for box_idx, transition in enumerate(model.transitions.values()):
            boxes.append({'parameter': str(transition.rate.key)})
            for controller in transition.control:
                win.append({'arg': vars[controller.key],
                            'call': box_idx + 1})
            for consumed in transition.consumed:
                win.append({'arg': vars[consumed.key],
                            'call': box_idx + 1})
                wn.append({'efflux': box_idx + 1,
                           'effusion': vars[consumed.key]})
            for produced in transition.produced:
                wa.append({'influx': box_idx + 1,
                           'infusion': vars[produced.key]})

        def tanvar_key(var_key):
            """Generate the key for the derivative."""
            # If the variable key is a simple string, we just add ' following
            # the example bilayer. If it's a tuple, we add the "derivative"
            if isinstance(var_key, str):
                return var_key + "'"
            else:
                return str(var_key + ('derivative',))

        qin = [{'variable': str(var.key)} for var in model.variables.values()]
        qout = [{'tanvar': tanvar_key(var.key)}
                for var in model.variables.values()]
        return {'Wa': wa, 'Win': win, 'Box': boxes, 'Qin': qin, 'Qout': qout,
                'Wn': wn}

    def save_bilayer(self, fname):
        """Save the generated bilayer into a JSON file."""
        with open(fname, 'w') as fh:
            json.dump(self.bilayer, fh, indent=1)
