__all__ = ['get_parseable_expression', 'revert_parseable_expression']


def get_parseable_expression(f):
    """Return an expression that can be parsed using sympy."""
    return f.replace('lambda', 'XXlambdaXX')


def revert_parseable_expression(f):
    """Return an expression to its original form."""
    return f.replace('XXlambdaXX', 'lambda')
