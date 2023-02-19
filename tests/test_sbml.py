from mira.sources.sbml.processor import parse_assignment_rule


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
