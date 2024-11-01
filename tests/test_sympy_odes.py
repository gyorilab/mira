import sympy

from mira.sources.sympy_ode import template_model_from_sympy_odes


def test_seir():
    # Define time variable
    t = sympy.symbols(r"t")

    # Define the time-dependent variables
    S, E, I, R = sympy.symbols(r"S E I R", cls=sympy.Function)

    # Define the parameters
    b, g, r = sympy.symbols(r"b g r")

    sympy_equations = [
        sympy.Eq(S(t).diff(t), - b * S(t) * I(t)),
        sympy.Eq(E(t).diff(t), b * S(t) * I(t) - r * E(t)),
        sympy.Eq(I(t).diff(t), r * E(t) - g * I(t)),
        sympy.Eq(R(t).diff(t), g * I(t))
    ]

    template_model_from_sympy_odes(sympy_equations)