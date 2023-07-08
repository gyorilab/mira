import sympy

from mira.sources.sbml.processor import parse_assignment_rule, \
    process_unit_definition


def test_parse_expr():
    expr = 'piecewise(Social_Distance_base * ' \
           'Government_induced_isolation_factor_0, and(gt(time, ' \
           'Time_government_action_0), lt(intermittent_time, ' \
           'Time_government_action_0 - lockdown_duration * ' \
           '(1 - timeFraction_lockdown_0))), Social_Distance_base)'
    rule = parse_assignment_rule(expr, {})
    # TODO: transform the piecewise/and/gt/lt functions to be valid
    # in formulas so the expression can be parsed
    assert rule is None


def test_unit_processing():
    class MockUnit:
        def __init__(self, kind, multiplier, exponent, scale):
            self.kind = kind
            self.multiplier = multiplier
            self.exponent = exponent
            self.scale = scale

    class MockUnitDefinition:
        def __init__(self, units):
            self.units = units

    day = MockUnit(28, 86400, -1, 0)
    person = MockUnit(12, 1, -1, 0)
    res = process_unit_definition(MockUnitDefinition([day, person]))
    assert res == 1 / (sympy.Symbol('day') * sympy.Symbol('person'))