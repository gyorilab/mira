"""Tests for the metamodel."""

from copy import deepcopy as _d
import json
import unittest
from copy import deepcopy

import pytest
import requests
import sympy

from mira.metamodel import *
from mira.metamodel import mathml_to_expression, expression_to_mathml, \
    UNIT_SYMBOLS
from mira.sources.amr.petrinet import state_to_concept, \
    template_model_from_amr_json
from tests import expression_yielder, remove_all_sympy, sorted_json_str

try:
    import sbmlmath
except ImportError:
    sbmlmath_available = False
else:
    sbmlmath_available = True

SBMLMATH_REQUIRED = unittest.skipUnless(sbmlmath_available, reason="SBMLMath package is not available")


class TestMetaModel(unittest.TestCase):
    """A test case for the metamodel."""
    # Set to None for full diff, remove to have default diff
    # https://docs.python.org/3/library/unittest.html#unittest.TestCase.maxDiff
    maxDiff = None

    def setUp(self) -> None:
        """Initialize the test case with shared concepts."""
        self.susceptible = Concept(name="susceptible population", identifiers={"ido": "0000514"})
        self.exposed = Concept(name="exposed", identifiers={"ido": "0000597"})
        self.infected = Concept(name="infected population", identifiers={"ido": "0000511"})
        self.asymptomatic = Concept(name="asymptomatic infected population", identifiers={"ido": "0000511"})
        self.immune = Concept(name="immune population", identifiers={"ido": "0000592"})

    def test_schema(self):
        """Test that the schema is up to date."""
        self.assertTrue(SCHEMA_PATH.is_file())
        self.assertEqual(
            get_json_schema(),
            json.loads(SCHEMA_PATH.read_text()),
            msg="Regenerate an updated JSON schema by running `python -m mira.metamodel.schema`",
        )

    def test_controlled_conversion(self):
        """Test instantiating the controlled conversion."""
        t1 = ControlledConversion(
            controller=self.immune,
            subject=self.susceptible,
            outcome=self.infected,
        )
        self.assertEqual(self.infected, t1.outcome)
        self.assertEqual(self.susceptible, t1.subject)
        self.assertEqual(self.immune, t1.controller)

    def test_natural_conversion(self):
        """Test natural conversions."""
        template = NaturalConversion(subject=self.exposed, outcome=self.infected)
        self.assertEqual(self.infected, template.outcome)
        self.assertEqual(self.exposed, template.subject)

    def test_group_controlled(self):
        """Test natural conversions."""
        t1 = GroupedControlledConversion(subject=self.susceptible, outcome=self.exposed,
                                         controllers=[self.infected, self.asymptomatic])
        self.assertEqual(self.exposed, t1.outcome)
        self.assertEqual(self.susceptible, t1.subject)
        self.assertIn(self.infected, t1.controllers)
        self.assertIn(self.asymptomatic, t1.controllers)

    def test_natural_degradation(self):
        t = NaturalDegradation(subject=self.infected)
        self.assertEqual(self.infected, t.subject)

    def test_natural_production(self):
        t = NaturalProduction(outcome=self.susceptible)
        self.assertEqual(self.susceptible, t.outcome)


def test_distributions():
    t = NaturalProduction(
        outcome=Concept(name="X"),
        rate=sympy.Symbol('gamma')
    )
    params = {
        'gamma': Parameter(
            name='gamma',
            value=0.5,
            distribution=Distribution(
                type='StandardUniform1',
                parameters={
                    'minimum': 0.0,
                    'maximum': 1.0,
                }
            )
        )
    }
    tm = TemplateModel(templates=[t], parameters=params)
    assert tm.parameters['gamma'].distribution.type == 'StandardUniform1'


def test_rate_law_to_mathml():
    expr = sympy.sympify('b1 * S_u * I_u')
    mathml = expression_to_mathml(expr)
    assert mathml == ('<apply><times/><ci>I_u</ci><ci>S_u</ci>'
                      '<ci>b1</ci></apply>')


@SBMLMATH_REQUIRED
def test_mathml_to_sympy():
    # 1
    xml_str = """<apply>
            <plus/>
            <apply>
                <times/>
                <ci> x </ci>
                <ci> y </ci>
            </apply>
            <apply>
                <times/>
                <ci> x </ci>
                <ci> z </ci>
            </apply>
        </apply>
    """
    expected = sympy.parse_expr("x*y + x*z")
    assert mathml_to_expression(xml_str) == expected

    # 2
    expression_str = (
        "I*S*kappa*(beta_c + (-beta_c + beta_s)/(1 + exp(-k*(-t + t_0))))/N"
    )
    sympy_expr = sympy.parse_expr(
        expression_str,
        local_dict={"I": sympy.Symbol("I"),
                    "S": sympy.Symbol("S"),
                    "kappa": sympy.Symbol("kappa"),
                    "beta_c": sympy.Symbol("beta_c"),
                    "beta_s": sympy.Symbol("beta_s"),
                    "k": sympy.Symbol("k"),
                    "t_0": sympy.Symbol("t_0"),
                    "t": sympy.Symbol("t"),
                    "N": sympy.Symbol("N")}
    )
    expression_mathml = (
        "<apply><divide/><apply><times/><ci>I</ci><ci>S</ci><ci>kappa</ci>"
        "<apply><plus/><ci>beta_c</ci><apply><divide/><apply><plus/><apply>"
        "<minus/><ci>beta_c</ci></apply><ci>beta_s</ci></apply><apply><plus/>"
        "<cn>1</cn><apply><exp/><apply><minus/><apply><times/><ci>k</ci>"
        "<apply><minus/><ci>t_0</ci><ci>t</ci></apply></apply></apply>"
        "</apply></apply></apply></apply></apply><ci>N</ci></apply>"
    )
    parsed_mathml = mathml_to_expression(expression_mathml)
    assert parsed_mathml == sympy_expr

    # 3
    sympy_expr = sympy.parse_expr("E*delta",
                                  local_dict={"E": sympy.Symbol("E")})

    expression_mathml = "<apply><times/><ci>E</ci><ci>delta</ci></apply>"
    assert sympy_expr.equals(mathml_to_expression(expression_mathml))

    # 4
    sympy_expr = sympy.parse_expr("I*gamma*(1 - alpha)",
                                  local_dict={"I": sympy.Symbol("I"),
                                              "gamma": sympy.Symbol("gamma"),
                                              "alpha": sympy.Symbol("alpha")})
    expression_mathml = (
        "<apply><times/><ci>I</ci><ci>gamma</ci><apply><minus/><cn>1</cn>"
        "<ci>alpha</ci></apply></apply>"
    )
    assert expression_to_mathml(sympy_expr) == expression_mathml

    # 5
    sympy_expr = sympy.parse_expr("I*alpha*rho",
                                  local_dict={"I": sympy.Symbol("I"),
                                              "alpha": sympy.Symbol("alpha"),
                                              "rho": sympy.Symbol("rho")})
    expression_mathml = (
        "<apply><times/><ci>I</ci><ci>alpha</ci><ci>rho</ci></apply>"
    )
    assert expression_to_mathml(sympy_expr) == expression_mathml


@SBMLMATH_REQUIRED
def test_from_askenet_petri():
    source_url = "https://raw.githubusercontent.com/DARPA-ASKEM/Model" \
                 "-Representations/main/petrinet/examples/sir.json"
    resp = requests.get(source_url)
    assert resp.status_code == 200
    model_json = resp.json()

    # Create symbols dict like in petrinet
    model = model_json['model']
    concepts = {}
    for state in model.get('states', []):
        concepts[state['id']] = state_to_concept(state)
    symbols = {state_id: sympy.Symbol(state_id) for state_id in concepts}
    ode_semantics = model_json.get("semantics", {}).get("ode", {})
    for parameter in ode_semantics.get('parameters', []):
        symbols[parameter['id']] = sympy.Symbol(parameter['id'])

    for expression_str, expression_mathml, is_unit in expression_yielder(
            model_json):
        # if checking units, use the UNIT_SYMBOLS dict
        local_dict = UNIT_SYMBOLS if "units" in expression_str else symbols
        assert mathml_to_expression(expression_mathml) == \
               sympy.parse_expr(expression_str, local_dict=local_dict)


@SBMLMATH_REQUIRED
def test_from_askenet_petri_mathml():
    # Get model
    source_url = "https://raw.githubusercontent.com/DARPA-ASKEM/Model" \
                 "-Representations/main/petrinet/examples/sir.json"
    resp = requests.get(source_url)
    assert resp.status_code == 200
    model_json_mathml = resp.json()

    # Make a deepcopy of the model
    model_json = deepcopy(model_json_mathml)

    # Remove sympy data from one copy
    remove_all_sympy(model_json_mathml)

    # Create models
    mathml_tm = template_model_from_amr_json(model_json_mathml)
    tm = template_model_from_amr_json(model_json)

    # Check equality
    mathml_str = sorted_json_str(mathml_tm.dict())
    org_str = sorted_json_str(tm.dict())
    assert mathml_str == org_str


def test_safe_parse_nfkc():
    eps = 'ϵ'
    eps_sym = sympy.Symbol(eps)
    assert safe_parse_expr(eps, local_dict={eps: eps_sym}) == eps_sym


def test_safe_parse_curly_braces():
    var = 'x_{a}'
    var_sym = sympy.Symbol('x_{a}')
    assert safe_parse_expr(var, local_dict={var: var_sym}) == var_sym

    var = 'x_{z}^{abc}'
    var_sym = sympy.Symbol('x_{z}^{abc}')
    assert safe_parse_expr(var, local_dict={var: var_sym}) == var_sym


def test_initial_expression_float():
    init = Initial(concept=Concept(name='x'), expression=1.0)
    assert isinstance(init.expression, SympyExprStr)
    assert isinstance(init.expression.args[0], sympy.Expr)
    init = Initial(concept=Concept(name='x'), expression=1)
    assert isinstance(init.expression, SympyExprStr)
    assert isinstance(init.expression.args[0], sympy.Expr)


def test_reversible_flux():
    from mira.modeling import Model
    from mira.modeling.amr.petrinet import template_model_to_petrinet_json
    t = ReversibleFlux(
        left=[Concept(name='x')],
        right=[Concept(name='y')],
    )
    # Make sure we can export to AMR
    tm = TemplateModel(templates=[t])
    model = Model(tm)
    amr = template_model_to_petrinet_json(tm)

