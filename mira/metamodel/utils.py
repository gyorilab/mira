__all__ = ['get_parseable_expression', 'revert_parseable_expression',
           'safe_parse_expr', 'SympyExprStr']

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
