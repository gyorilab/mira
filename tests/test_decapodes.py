from mira.examples.decapodes.decapodes_examples import (
    get_oscillator_decapode,
    get_oscillator_decapode_json,
    get_friction_decapode,
    get_friction_decapode_json
)

from mira.sources.acsets.decapodes import process_decapode
from mira.metamodel.decapodes import Variable, RootVariable, TangentVariable
import requests
import sympy

DERIVATIVE_FUNCTION = sympy.Function("∂ₜ")


def test_oscillator_decapode():
    decapode = get_oscillator_decapode()
    json_decapode = get_oscillator_decapode_json()

    assert len(decapode.variables) == 6
    for var_json, var_obj in zip(json_decapode['Var'],
                                 decapode.variables.values()):
        assert var_json['name'] == var_obj.name
        assert var_json['type'] == var_obj.type

    assert len(decapode.tangent_variables) == 2
    for tvar_json, tvar_obj in zip(json_decapode['TVar'],
                                   decapode.tangent_variables.values()):
        assert tvar_obj.incl_var == decapode.variables[tvar_json['incl']]

    assert len(decapode.op1s) == 2
    for op1_json, op1_obj in zip(json_decapode['Op1'], decapode.op1s.values()):
        assert decapode.variables[op1_json['src']] == op1_obj.src
        assert decapode.variables[op1_json['tgt']] == op1_obj.tgt
        assert op1_json['op1'] == op1_obj.function_str

    assert len(decapode.op2s) == 2
    for op2_json, op2_obj in zip(json_decapode['Op2'], decapode.op2s.values()):
        assert decapode.variables[op2_json['proj1']] == op2_obj.proj1
        assert decapode.variables[op2_json['proj2']] == op2_obj.proj2
        assert decapode.variables[op2_json['res']] == op2_obj.res
        assert op2_json['op2'] == op2_obj.function_str

    assert len(decapode.summations) == 0

    for var in decapode.variables.values():
        if var.id == 5:
            assert isinstance(var, RootVariable)
            assert len(var.expression) == 2
            assert var.expression[0] == DERIVATIVE_FUNCTION(
                DERIVATIVE_FUNCTION(sympy.Symbol('X')))
            assert var.expression[1] == sympy.Symbol('-1') * sympy.sympify(
                'X*k')
        else:
            assert isinstance(var, Variable)
            if isinstance(var.expression, sympy.Symbol):
                assert var.expression == sympy.Symbol(var.name)

            # Check for expressions of non-base level variables that aren't
            # root variables
            elif var.id == 2:
                DERIVATIVE_FUNCTION(var.name)
            elif var.id == 4:
                assert var.expression == sympy.Symbol('-1') * sympy.Symbol(
                    'k')


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
        assert isinstance(tvar_obj.incl_var, RootVariable)

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

    for var in decapode.variables.values():
        if var.id == 6:
            assert isinstance(var, RootVariable)
            assert len(var.expression) == 2
            assert var.expression[0] == DERIVATIVE_FUNCTION(sympy.Symbol('Q'))
            assert var.expression[1] == (
                sympy.sympify('V*κ') + sympy.Symbol('λ') *
                (sympy.Symbol('Q') - sympy.Symbol('Q₀')))
        else:
            assert isinstance(var, Variable)
            if isinstance(var.expression, sympy.Symbol):
                assert var.expression == sympy.Symbol(var.name)

            # Check for expressions of non-base level variables that aren't
            # root variables
            elif var.id == 7:
                assert var.expression == sympy.sympify('V*κ')
            elif var.id == 8:
                assert var.expression == sympy.Symbol('λ') * (sympy.Symbol(
                    'Q') - sympy.Symbol('Q₀'))
            elif var.id == 9:
                assert var.expression == (sympy.Symbol(
                    'Q') - sympy.Symbol('Q₀'))


def test_ice_decapode():
    json_decapode = requests.get(
        'https://raw.githubusercontent.com/ciemss/Decapodes.jl'
        '/sa_climate_modeling/examples/climate/ice_dynamics.json').json()

    decapode = process_decapode(json_decapode)

    assert len(decapode.variables) == 30
    for var_json, var_obj in zip(json_decapode['Var'],
                                 decapode.variables.values()):
        assert var_json['name'] == var_obj.name
        assert var_json['type'] == var_obj.type

    assert len(decapode.tangent_variables) == 1
    for tvar_json, tvar_obj in zip(json_decapode['TVar'],
                                   decapode.tangent_variables.values()):
        assert tvar_obj.incl_var == decapode.variables[tvar_json['incl']]
        assert isinstance(tvar_obj.incl_var, RootVariable)

    assert len(decapode.op1s) == 10
    for op1_json, op1_obj in zip(json_decapode['Op1'], decapode.op1s.values()):
        assert decapode.variables[op1_json['src']] == op1_obj.src
        assert decapode.variables[op1_json['tgt']] == op1_obj.tgt
        assert op1_json['op1'] == op1_obj.function_str

    assert len(decapode.op2s) == 11
    for op2_json, op2_obj in zip(json_decapode['Op2'], decapode.op2s.values()):
        assert decapode.variables[op2_json['proj1']] == op2_obj.proj1
        assert decapode.variables[op2_json['proj2']] == op2_obj.proj2
        assert decapode.variables[op2_json['res']] == op2_obj.res
        assert op2_json['op2'] == op2_obj.function_str

    assert len(decapode.summations) == 2
    assert decapode.summations[1].sum == decapode.variables[json_decapode["Σ"][
        0]['sum']]

    assert len(decapode.summations[1].summands) == 2
    for summand_json, summand_var in zip(json_decapode['Summand'],
                                         decapode.summations[1].summands):
        assert decapode.variables[summand_json['summand']] == summand_var

    assert len(decapode.summations[2].summands) == 2
    for summand_json, summand_var in zip(json_decapode['Summand'],
                                         decapode.summations[1].summands):
        assert decapode.variables[summand_json['summand']] == summand_var

    for var in decapode.variables.values():
        if var.id == 4:
            assert isinstance(var, RootVariable)
            assert len(var.expression) == 2
            assert var.expression[0] == DERIVATIVE_FUNCTION(sympy.Symbol('h'))
        else:
            assert isinstance(var, Variable)
            if isinstance(var.expression, sympy.Symbol):
                assert var.expression == sympy.Symbol(var.name)
