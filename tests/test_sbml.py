import os
import sympy

from mira.sources.sbml.processor import parse_assignment_rule, \
    process_unit_definition
from mira.sources.sbml import template_model_from_sbml_file, template_model_from_sbml_string
from mira.modeling.sbml import template_model_to_sbml_string


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


def test_distr_processing():
    HERE = os.path.dirname(os.path.abspath(__file__))
    model_file = os.path.join(HERE, 'ABCD_model.xml')

    tm = template_model_from_sbml_file(model_file)
    s = template_model_to_sbml_string(tm)
    tm1 = template_model_from_sbml_string(s)

    lambda x: float(x.args[0])

    # GeneA_init should be uniform 0 10
    assert tm1.parameters['GeneA_init'].distribution.type == 'Uniform1'
    assert tm1.parameters['GeneA_init'].distribution.parameters['minimum'].args[0] == 0
    assert tm1.parameters['GeneA_init'].distribution.parameters['maximum'].args[0] == 10

    # GeneB init should be normal 2.7 10.5
    assert tm1.parameters['GeneB_init'].distribution.type == 'Normal1'
    assert float(tm1.parameters['GeneB_init'].distribution.parameters['mean'].args[0]) == 2.7
    assert float(tm1.parameters['GeneB_init'].distribution.parameters['stdev'].args[0]) == 10.5

    # GeneC_init should be poisson 0.1
    assert tm1.parameters['GeneC_init'].distribution.type == 'Poisson1'
    assert float(tm1.parameters['GeneC_init'].distribution.parameters['rate'].args[0]) == 0.1

    # GeneD_init should be binomial 10 0.1
    assert tm1.parameters['GeneD_init'].distribution.type == 'Binomial1'
    assert tm1.parameters['GeneD_init'].distribution.parameters['numberOfTrials'].args[0] == 10
    assert float(tm1.parameters['GeneD_init'].distribution.parameters['probability'].args[0]) == 0.1

    for p, v in tm1.parameters.items():
        if 'compartment' in p or 'init' in p or "DefaultCompartment" == p:
            continue
        assert v.distribution is not None
        assert v.distribution.type == 'Uniform1'
        assert v.distribution.parameters
