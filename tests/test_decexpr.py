from mira.examples.decapodes.decapodes_examples import (
    get_oscillator_decaexpr,
    get_friction_decaexpr,
)


def test_oscillator_decaexpr():
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

    assert len(oscillator_decapode.op1s) == 2  # Have dX/dt and dV/dt
    assert (
        len(oscillator_decapode.op2s) == 2
    )  # Have -1*k=mult_1, mult_1*X=mult_2
    assert len(oscillator_decapode.summations) == 0  # No summations
    assert (
        len(oscillator_decapode.tangent_variables) == 2
    )  # Have dX/dt and dV/dt


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
