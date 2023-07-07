"""Test functions in the mira.metamodel.io module."""
from copy import deepcopy

import requests
import sympy

from mira.metamodel import UNIT_SYMBOLS
from mira.metamodel.io import mathml_to_expression, expression_to_mathml
from mira.sources.askenet import petrinet

from mira.sources.askenet.petrinet import state_to_concept
from tests import sorted_json_str, _expression_yielder, _remove_all_sympy


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
    assert expression_to_mathml(sympy_expr) == expression_mathml

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

    for expression_str, expression_mathml, is_unit in _expression_yielder(
            model_json):
        # if checking units, use the UNIT_SYMBOLS dict
        local_dict = UNIT_SYMBOLS if "units" in expression_str else symbols
        assert mathml_to_expression(expression_mathml) == \
               sympy.parse_expr(expression_str, local_dict=local_dict)


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
    _remove_all_sympy(model_json_mathml)

    # Create models
    mathml_tm = petrinet.template_model_from_askenet_json(model_json_mathml)
    tm = petrinet.template_model_from_askenet_json(model_json)

    # Check equality
    mathml_str = sorted_json_str(mathml_tm.dict())
    org_str = sorted_json_str(tm.dict())
    assert mathml_str == org_str
