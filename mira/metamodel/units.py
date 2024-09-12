from pydantic import ConfigDict

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
from pydantic import BaseModel, Field, field_serializer
from .utils import SympyExprStr


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


class Unit(BaseModel):
    """A unit of measurement."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    expression: SympyExprStr = Field(
        description="The expression for the unit."
    )

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Unit":
        # Use get_sympy from amr.petrinet, but avoid circular import
        from mira.sources.amr.petrinet import get_sympy
        data["expression"] = get_sympy(data, local_dict=UNIT_SYMBOLS)
        assert data.get('expression') is None or not isinstance(
            data['expression'], str
        )
        return cls(**data)

    @classmethod
    def model_validate(cls, obj):
        if isinstance(obj, dict) and 'expression' in obj:
            obj['expression'] = SympyExprStr(obj['expression'])
        return super().model_validate(obj)

    @field_serializer('expression')
    def serialize_expression(self, expression):
        return str(expression)


person_units = Unit(expression=sympy.Symbol('person'))
day_units = Unit(expression=sympy.Symbol('day'))
per_day_units = Unit(expression=1/sympy.Symbol('day'))
dimensionless_units = Unit(expression=sympy.Integer('1'))
per_day_per_person_units = Unit(expression=1/(sympy.Symbol('day')*sympy.Symbol('person')))
