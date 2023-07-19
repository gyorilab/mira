__all__ = ['get_parseable_expression', 'revert_parseable_expression',
           'safe_parse_expr', 'SympyExprStr', 'summarize_concepts']

from collections import Counter

import sympy


def get_parseable_expression(s: str) -> str:
    """Return an expression that can be parsed using sympy."""
    return s.replace('lambda', 'XXlambdaXX')


def revert_parseable_expression(s: str) -> str:
    """Return an expression to its original form."""
    return s.replace('XXlambdaXX', 'lambda')


def safe_parse_expr(s: str, local_dict=None) -> sympy.Expr:
    """Parse an expression that may contain lambda functions."""
    return sympy.parse_expr(get_parseable_expression(s),
                            local_dict={get_parseable_expression(k): v
                                        for k, v in local_dict.items()}
                                        if local_dict else None)


class SympyExprStr(sympy.Expr):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, cls):
            return v
        return cls(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string", example="2*x")

    def __str__(self):
        return super().__str__()[len(self.__class__.__name__)+1:-1]

    def __repr__(self):
        return str(self)


def summarize_concepts(template_model):
    """Create a summary dataframe of concepts appearances and
    their units in compartments and parameters.
    """
    import pandas as pd
    units = {}
    counts = Counter()

    for template in template_model.templates:
        for concept in template.get_concepts():
            unit = str(concept.units.expression) if concept.units else ""
            key = "concept", concept.get_curie_str(), concept.name
            units[key] = unit
            counts[key] += 1

            for context_concept in concept.context.values():
                key = "context", context_concept, ""
                units[key] = None
                counts[key] += 1

    for key, concept in template_model.parameters.items():
        unit = str(concept.units.expression) if concept.units else ""
        key = "parameter", "", concept.name
        units[key] = unit

    return pd.DataFrame(
        [(*k, v, counts.get(k, 0)) for k, v in units.items()],
        columns=["type", "curie", "name", "unit", "count"]
    )
