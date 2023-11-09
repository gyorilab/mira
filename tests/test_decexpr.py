import sympy

from mira.examples.decapodes.decapodes_examples import (
    get_oscillator_decaexpr,
    get_friction_decaexpr,
)


def test_oscillator_decaexpr():
    # Check that variable types are correct (Form0,  Form1, Literal, infer,
    # Constant, Dualform_1, Dualform_2, etc.)
    # Check that we have the correct number of op1, op2, tangent variables,
    # and summations
    # Check that the op1, op2, tangent variables, and summations are the
    # expected ones (check source, target etc.)
    # Check that expressions are correct...

    oscillator_decapode = get_oscillator_decaexpr()
    # Original equation:
    # ∂ₜ(X) = V
    # ∂ₜ(∂ₜ(X)) = ∂ₜ(V) = -1*k*X

    variable_set = {
        "V",
        "X",
        "k",
        "-1",
        "∂ₜ(X)",
        "∂ₜ(V)",
        "mult_1",
        "mult_2",
    }

    assert variable_set == {
        str(v) for v in oscillator_decapode.variables.values()
    }
    name_to_variable = {
        v.name: v for v in oscillator_decapode.variables.values()
    }
    assert name_to_variable["X"].type == "Form0"
    assert name_to_variable["V"].type == "Form0"
    assert name_to_variable["k"].type == "Constant"
    assert name_to_variable["-1"].type == "Literal"
    assert name_to_variable["∂ₜ(X)"].type == "infer"
    assert name_to_variable["∂ₜ(V)"].type == "infer"
    assert name_to_variable["mult_1"].type == "infer"
    assert name_to_variable["mult_2"].type == "infer"

    assert len(oscillator_decapode.op1s) == 2  # Have dX/dt and dV/dt
    unary_targets = {op.tgt.name for op in oscillator_decapode.op1s.values()}
    assert unary_targets == {"∂ₜ(X)", "∂ₜ(V)"}
    unary_args = {op.src.name for op in oscillator_decapode.op1s.values()}
    assert unary_args == {"X", "V"}

    assert (
        len(oscillator_decapode.op2s) == 2
    )  # Have -1*k=mult_1, mult_1*X=mult_2
    for op2 in oscillator_decapode.op2s.values():
        assert (
            {op2.proj1.name, op2.proj2.name} == {"-1", "k"} or
            {op2.proj1.name, op2.proj2.name} == {"mult_1", "X"}
        )

    assert len(oscillator_decapode.summations) == 0  # No summations

    assert (
        len(oscillator_decapode.tangent_variables) == 2
    )  # Have dX/dt and dV/dt
    tangent_variable_names = {
        v.incl_var.name for v in oscillator_decapode.tangent_variables.values()
    }
    assert tangent_variable_names == {"∂ₜ(X)", "∂ₜ(V)"}

    # Check that expressions are correct
    dt = sympy.Function("∂ₜ")
    X, V, k, minus_one = sympy.symbols("X V k -1")
    assert name_to_variable["k"].expression == k
    assert name_to_variable["-1"].expression == minus_one
    assert name_to_variable["X"].expression == X
    assert name_to_variable["V"].expression == V
    assert name_to_variable["∂ₜ(X)"].expression == dt(X)
    assert name_to_variable["∂ₜ(V)"].expression == dt(V)
    assert name_to_variable["mult_1"].expression == minus_one * k
    assert name_to_variable["mult_2"].expression == name_to_variable["mult_1"].expression * X


def test_friction_decaexpr():
    friction_decapode = get_friction_decaexpr()
    # Original equation:
    # ∂ₜ(Q) = κ*V + λ*(Q-Q₀)

    variable_set = {
        "V",
        "Q",
        "κ",
        "λ",
        "Q₀",
        "∂ₜ(Q)",
        "mult_1",
        "sub_1",
        "mult_2",
        "sum_1",
    }
    assert variable_set == {
        str(v) for v in friction_decapode.variables.values()
    }
    assert len(friction_decapode.op1s) == 1  # Only have dQ/dt
    assert len(friction_decapode.op2s) == 3  # κ*V=mult_1, Q-Q₀=sub_1,
    # and λ*sub_1=mult_2
    assert (
        len(friction_decapode.summations) == 1
    )  # Only have mult_1+mult_2=sum_1
    assert len(friction_decapode.tangent_variables) == 1  # Only have dQ/dt
