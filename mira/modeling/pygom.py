"""This module implements generation into PyGOM models, see
https://ukhsa-collaboration.github.io/pygom.
"""

__all__ = ["PyGOMModel", "template_model_to_pygom"]

from itertools import zip_longest

import sympy
from pygom import Event, SimulateOde, Transition

from mira.metamodel import TemplateModel

from . import Model


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
        self.parameters = {p.key: p.value for p in model.parameters.values()
                           if not p.placeholder}
        self.states = [var.concept.name for var in model.variables.values()]
        # PyGOM interprets the symbol t as time
        time_subs = {sympy.Symbol(tm.time.name): sympy.Symbol('t')} \
            if tm.time else {}

        self.events = []
        for transition in model.transitions.values():
            transitions = []
            for consumed, produced in zip_longest(transition.consumed,
                                                  transition.produced):
                origin = consumed.concept.name if consumed else None
                destination = produced.concept.name if produced else None
                ttype = 'T' if consumed and produced else \
                    ('D' if consumed else 'B')
                transitions.append(Transition(origin=origin,
                                              destination=destination,
                                              transition_type=ttype))
            rate = transition.template.rate_law.subs(time_subs)
            self.events.append(Event(transition_list=transitions,
                                     rate=str(rate)))

        self.pygom_model = SimulateOde(state=self.states,
                                       param=list(self.parameters),
                                       event=self.events)
        values = [(k, v) for k, v in self.parameters.items()
                  if v is not None]
        if values:
            self.pygom_model.parameters = values
        initials = [var.data['expression'] for var in
                    model.variables.values()]
        if all(initial is not None for initial in initials):
            self.pygom_model.initial_values = (
                [float(initial.subs(self.parameters))
                 for initial in initials], 0
            )


def template_model_to_pygom(tm: TemplateModel) -> SimulateOde:
    """Return a PyGOM SimulateOde model from a template model."""
    return PyGOMModel(Model(tm)).pygom_model
