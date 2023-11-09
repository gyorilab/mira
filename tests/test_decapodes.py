from mira.examples.decapodes.decapodes_examples import (
    get_oscillator_decapode,
    get_friction_decapode
)

from mira.sources.acsets.decapodes import process_decapode
from mira.metamodel.decapodes import Variable, RootVariable
import requests
import sympy


def test_oscillator_decapode():
    decapode = get_oscillator_decapode()

    assert len(decapode.variables) == 6
    assert decapode.variables[1].type == 'Form0'
    assert decapode.variables[1].name == 'X'

    assert decapode.variables[2].type == 'Form0'
    assert decapode.variables[2].name == 'V'

    assert decapode.variables[3].type == 'Constant'
    assert decapode.variables[3].name == 'k'

    assert decapode.variables[4].type == 'infer'
    assert decapode.variables[4].name == 'mult_1'

    assert decapode.variables[5].type == 'infer'
    assert decapode.variables[5].name == "V̇"

    assert decapode.variables[6].type == 'Literal'
    assert decapode.variables[6].name == '-1'

    assert len(decapode.tangent_variables) == 2
    assert decapode.tangent_variables[1].incl_var.id == 2
    assert decapode.tangent_variables[2].incl_var.id == 5

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
            derivative_function = sympy.Function("∂ₜ")
            assert isinstance(var, RootVariable)
            assert len(var.expression) == 2
            assert var.expression[0] == derivative_function(
                derivative_function(sympy.Symbol('X')))
        else:
            assert isinstance(var, Variable)
            if isinstance(var.expression,sympy.Symbol):
                assert var.expression == sympy.Symbol(var.name)


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
    get_friction_decapode()


def test_ice_decapode():
    decapode = process_decapode(requests.get(
        'https://raw.githubusercontent.com/ciemss/Decapodes.jl'
        '/sa_climate_modeling/examples/climate/ice_dynamics.json').json())

    print()
