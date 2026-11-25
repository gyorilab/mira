"""This module implements generation into PyGOM models, see
https://ukhsa-collaboration.github.io/pygom.
"""

__all__ = ["PyGOMModel", "template_model_to_pygom"]

import keyword
from collections import Counter
from itertools import zip_longest

import sympy
from pygom import Event, SimulateOde, Transition

from mira.metamodel import TemplateModel

from . import Model


def _n(name: str) -> str:
    return f'{name}_' if keyword.iskeyword(name) else name


class PyGOMModel:
    """A class representing a PyGOM model."""

    def __init__(self, model: Model):
        """Instantiate a PyGOM model from a generic transition model.

        Parameters
        ----------
        model:
            The pre-compiled transition model
        """
        tm = model.template_model
        self.states = [_n(var.concept.name)
                       for var in model.variables.values()]
        self.parameters = {_n(p.key): p.value
                           for p in model.parameters.values()
                           if not p.placeholder}

        self.events = []
        for idx, transition in enumerate(model.transitions.values()):
            consumed = Counter(_n(var.concept.name)
                               for var in transition.consumed)
            produced = Counter(_n(var.concept.name)
                               for var in transition.produced)
            # A concept that is both consumed and produced cancels out,
            # PyGOM doesn't allow a transition from a state to itself
            transitions = []
            for origin, destination in \
                    zip_longest((consumed - produced).elements(),
                                (produced - consumed).elements()):
                ttype = 'T' if origin and destination else \
                    ('D' if origin else 'B')
                transitions.append(Transition(origin=origin,
                                              destination=destination,
                                              transition_type=ttype))

            rate = transition.template.rate_law
            # Without a rate law, use mass action with a new rate parameter
            # that has no value
            if rate is None:
                self.parameters[f'rate_{idx}'] = None
                rate = sympy.Symbol(f'rate_{idx}') * sympy.Mul(*[
                    sympy.Symbol(var.concept.name) for var in
                    transition.consumed + transition.control
                ])
            subs = {symbol: sympy.Symbol(_n(symbol.name))
                    for symbol in rate.free_symbols}
            # PyGOM interprets the symbol t as time
            if tm.time:
                subs[sympy.Symbol(tm.time.name)] = sympy.Symbol('t')
            rate = rate.subs(subs)
            self.events.append(Event(transition_list=transitions,
                                     rate=str(rate)))

        self.pygom_model = SimulateOde(state=self.states,
                                       param=list(self.parameters),
                                       event=self.events)
        values = [(k, v) for k, v in self.parameters.items()
                  if v is not None]
        if values:
            self.pygom_model.parameters = values

        parameter_values = {sympy.Symbol(p.key): p.value
                            for p in model.parameters.values()
                            if not p.placeholder and p.value is not None}
        initials = [var.data['expression'] for var in
                    model.variables.values()]
        if all(initial is not None for initial in initials):
            initials = [initial.subs(parameter_values)
                        for initial in initials]
            if all(initial.is_number for initial in initials):
                self.pygom_model.initial_values = (
                    [float(initial) for initial in initials], 0
                )


def template_model_to_pygom(tm: TemplateModel) -> SimulateOde:
    """Return a PyGOM SimulateOde model from a template model."""
    return PyGOMModel(Model(tm)).pygom_model
