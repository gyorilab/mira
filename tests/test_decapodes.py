from mira.examples.decapodes.decapodes_examples import (
    get_oscillator_decapode,
    get_oscillator_decapode_json,
    get_friction_decapode,
    get_friction_decapode_json
)

from mira.sources.acsets.decapodes import process_decapode
from mira.metamodel.decapodes import Variable, RootVariable
import requests
import sympy


def test_oscillator_decapode():
    decapode = get_oscillator_decapode()
    json_decapode = get_oscillator_decapode_json()
    derivative_function = sympy.Function("∂ₜ")

    assert len(decapode.variables) == 6
    assert {var.name for var in decapode.variables.values()} == {var['name']
                                                                 for var in
                                                                 json_decapode[
                                                                     'Var']}
    assert {var.type for var in decapode.variables.values()} == {var['type']
                                                                 for var in
                                                                 json_decapode
                                                                 ['Var']}

    assert len(decapode.tangent_variables) == 2
    assert (decapode.tangent_variables[1].incl_var ==
            decapode.variables[json_decapode['TVar'][0]['incl']])
    assert (decapode.tangent_variables[2].incl_var ==
            decapode.variables[json_decapode['TVar'][1]['incl']])

    assert len(decapode.op1s) == 2
    assert decapode.op1s[1].src.id == 1
    assert decapode.op1s[1].tgt.id == 2
    assert decapode.op1s[1].function_str == '∂ₜ'

    assert decapode.op1s[2].src.id == 2
    assert decapode.op1s[2].tgt.id == 5
    assert decapode.op1s[2].function_str == '∂ₜ'

    assert len(decapode.op2s) == 2
    assert decapode.op2s[1].proj1.id == 6
    assert decapode.op2s[1].proj2.id == 3
    assert decapode.op2s[1].res.id == 4
    assert decapode.op2s[1].function_str == '*'

    assert decapode.op2s[2].proj1.id == 4
    assert decapode.op2s[2].proj2.id == 1
    assert decapode.op2s[2].res.id == 5
    assert decapode.op2s[2].function_str == '*'

    assert len(decapode.summations) == 0

    for var in decapode.variables.values():
        if var.id == 5:
            assert isinstance(var, RootVariable)
            assert len(var.expression) == 2
            assert var.expression[0] == derivative_function(
                derivative_function(sympy.Symbol('X')))
            assert var.expression[1] == sympy.Symbol('-1') * sympy.sympify(
                'X*k')
        else:
            assert isinstance(var, Variable)
            if isinstance(var.expression, sympy.Symbol):
                assert var.expression == sympy.Symbol(var.name)
            elif var.id == 4:
                assert var.expression == sympy.Symbol('-1') * sympy.Symbol(
                    'k')
            elif var.id == 2:
                derivative_function(var.name)

    # assert {var.name for var in decapode.variables.values()} == {
    #     ...  # Check that the correct symbols are present
    # }
    # Check that variable types are correct (Form0,  Form1, Literal, infer,
    # Constant, Dualform_1, Dualform_2, etc.)
    # Check that we have the correct number of op1, op2, tangent variables,
    # and summations
    # Check that the op1, op2, tangent variables, and summations are the
    # expected ones (check source, target etc.)
    # Check that expressions are correct...


def test_friction_decapode():
    decapode = get_friction_decapode()
    json_decapode = get_friction_decapode_json()

    assert len(decapode.variables) == 9
    for var_json, var_obj in zip(json_decapode['Var'],
                                 decapode.variables.values()):
        assert var_json['name'] == var_obj.name
        assert var_json['type'] == var_obj.type

    assert len(decapode.tangent_variables) == 1
    for tvar_json, tvar_obj in zip(json_decapode['TVar'],
                                   decapode.tangent_variables.values()):
        assert tvar_obj.incl_var == decapode.variables[tvar_json['incl']]
        assert len(tvar_obj.incl_var.expression) == 2

    assert len(decapode.op1s) == 1
    for op1_json, op1_obj in zip(json_decapode['Op1'], decapode.op1s.values()):
        assert decapode.variables[op1_json['src']] == op1_obj.src
        assert decapode.variables[op1_json['tgt']] == op1_obj.tgt
        assert op1_json['op1'] == op1_obj.function_str

    assert len(decapode.op2s) == 3
    for op2_json, op2_obj in zip(json_decapode['Op2'], decapode.op2s.values()):
        assert decapode.variables[op2_json['proj1']] == op2_obj.proj1
        assert decapode.variables[op2_json['proj2']] == op2_obj.proj2
        assert decapode.variables[op2_json['res']] == op2_obj.res
        assert op2_json['op2'] == op2_obj.function_str

    assert len(decapode.summations) == 1
    assert decapode.summations[1].sum == decapode.variables[json_decapode["Σ"][
        0]['sum']]

    assert len(decapode.summations[1].summands) == 2
    for summand_json, summand_var in zip(json_decapode['Summand'],
                                         decapode.summations[1].summands):
        assert decapode.variables[summand_json['summand']] == summand_var


def test_ice_decapode():
    decapode = process_decapode(requests.get(
        'https://raw.githubusercontent.com/ciemss/Decapodes.jl'
        '/sa_climate_modeling/examples/climate/ice_dynamics.json').json())

    print()
