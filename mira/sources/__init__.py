"""Sources of models."""


def clean_formula(f):
    """Return an expression that can be parsed using sympy."""
    return f.replace('lambda', 'XXlambdaXX')
