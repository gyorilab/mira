__all__ = ['get_parseable_expression', 'revert_parseable_expression',
           'safe_parse_expr', 'SympyExprStr', 'sanity_check_tm']

import sympy
import re
import unicodedata


def get_parseable_expression(s: str) -> str:
    """Return an expression that can be parsed using sympy."""
    # Handle lambda which cannot be parsed by sympy
    s = s.replace('lambda', 'XXlambdaXX')
    # Handle dots which also cannot be parsed
    s = re.sub(r'\.(?=\D)', 'XX_XX', s)
    # Handle curly braces which are not allowed in sympy
    s = s.replace('{', 'XXCBO').replace('}', 'XXCBC')
    s = unicodedata.normalize('NFKC', s)
    return s


def revert_parseable_expression(s: str) -> str:
    """Return an expression to its original form."""
    s = s.replace('XXCBO', '{').replace('XXCBC', '}')
    s = s.replace('XX_XX', '.')
    s = s.replace('XXlambdaXX', 'lambda')
    return s


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


def sanity_check_tm(tm):
    """Apply a short sanity check to a template model."""
    assert tm.templates
    all_concept_names = set(tm.get_concepts_name_map())
    all_parameter_names = set(tm.parameters)
    all_symbols = all_concept_names | all_parameter_names | ({tm.time.name} if tm.time else set())
    for template in tm.templates:
        assert template.rate_law
        symbols = template.rate_law.args[0].free_symbols
        for symbol in symbols:
            assert symbol.name in all_symbols, f"missing symbol: {symbol.name}"
    all_initial_names = {init.concept.name for init in tm.initials.values()}
    for concept in all_concept_names:
        assert concept in all_initial_names
