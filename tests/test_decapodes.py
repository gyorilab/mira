from mira.examples.decapodes.decapodes_examples import (
    get_oscillator_decapode,
    get_friction_decapode
)


def test_oscillator_decapode():
    decapode = get_oscillator_decapode()

    assert len(decapode.variables) == ...

    assert {var.name for var in decapode.variables.values()} == {
        ...  # Check that the correct symbols are present
    }
    # Check that variable types are correct (Form0,  Form1, Literal, infer,
    # Constant, Dualform_1, Dualform_2, etc.)
    # Check that we have the correct number of op1, op2, tangent variables,
    # and summations
    # Check that the op1, op2, tangent variables, and summations are the
    # expected ones (check source, target etc.)
    # Check that expressions are correct...


def test_friction_decapode():
    get_friction_decapode()
