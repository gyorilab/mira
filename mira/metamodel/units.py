__all__ = [
    'Unit',
    'person_units',
    'day_units',
    'per_day_units',
    'dimensionless_units',
    'per_day_per_person_units',
    'UNIT_SYMBOLS'
]

import os
from typing import Dict, Any

import sympy


def load_units():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        os.pardir, 'dkg', 'resources', 'unit_names.tsv')
    with open(path, 'r') as fh:
        units = {}
        for line in fh.readlines():
            symbol = line.strip()
            units[symbol] = sympy.Symbol(symbol)
    return units


UNIT_SYMBOLS = load_units()


class Unit:
    """A unit of measurement.

    Attributes
    ----------
    expression : sympy.Expr
        The expression for the unit.
    """

    def __init__(self, expression: sympy.Expr):
        self.expression = expression

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Unit":
        from mira.sources.util import get_sympy
        new_data = data.copy()
        new_data["expression"] = get_sympy(data, local_dict=UNIT_SYMBOLS)
        assert (new_data.get('expression') is None or
                not isinstance(new_data.get('expression'), str))
        return cls(new_data["expression"])

    def to_json(self) -> dict:
        return {"expression": str(self.expression)}

    def __repr__(self):
        return f"Unit({self.expression})"


person_units = Unit(sympy.Symbol('person'))
day_units = Unit(sympy.Symbol('day'))
per_day_units = Unit(1/sympy.Symbol('day'))
dimensionless_units = Unit(sympy.Integer('1'))
per_day_per_person_units = Unit(1/(sympy.Symbol('day')*sympy.Symbol('person')))
