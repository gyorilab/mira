__all__ = ['get_parseable_expression', 'revert_parseable_expression',
           'safe_parse_expr']

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
                                        for k, v in local_dict.items()})