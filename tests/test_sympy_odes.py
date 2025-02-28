import sympy
from sympy import Function, symbols, Eq, Symbol

from mira.metamodel import StaticConcept
from mira.sources.sympy_ode import template_model_from_sympy_odes


def sympy_eq(expr1, expr2):
    if sympy.expand(expr1 - expr2) == 0:
        return True
    else:
        return False


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

    tm = template_model_from_sympy_odes(sympy_equations)
    assert set(tm.parameters) == {'r', 'b', 'g'}
    assert len(tm.templates) == 3
    infection = tm.templates[0]
    prog = tm.templates[1]
    recovery = tm.templates[2]
    assert infection.subject.name == 'S'
    assert infection.controller.name == 'I'
    assert infection.outcome.name == 'E'
    assert prog.subject.name == 'E'
    assert prog.outcome.name == 'I'
    assert recovery.subject.name == 'I'
    assert recovery.outcome.name == 'R'


def test_branching():
    # Define time variable
    t = sympy.symbols(r"t")

    # Define the time-dependent variables
    H, D, R = sympy.symbols(r"H D R", cls=sympy.Function)

    # Define the parameters
    a, b = sympy.symbols(r"a b")

    sympy_equations = [
        sympy.Eq(H(t).diff(t), - a * b * H(t) - (1 - a) * b * H(t)),
        sympy.Eq(D(t).diff(t), a * b * H(t)),
        sympy.Eq(R(t).diff(t), (1 - a) * b * H(t)),
    ]

    tm = template_model_from_sympy_odes(sympy_equations)
    assert set(tm.parameters) == {'a', 'b'}
    assert len(tm.templates) == 2
    death = tm.templates[0]
    recovery = tm.templates[1]
    assert death.type == 'NaturalConversion'
    assert death.subject.name == 'H'
    assert death.outcome.name == 'D'
    # Test for rate law as a sympy expression
    assert death.rate_law.args[0] == a * b * sympy.Symbol('H')
    assert recovery.type == 'NaturalConversion'
    assert recovery.subject.name == 'H'
    assert recovery.outcome.name == 'R'
    # Test for rate law as a sympy expression
    assert recovery.rate_law.args[0] == (1 - a) * b * sympy.Symbol('H')


def test_branching_explicit_parentheses():
    # Define time variable
    t = sympy.symbols(r"t")

    # Define the time-dependent variables
    H, D, R = sympy.symbols(r"H D R", cls=sympy.Function)

    # Define the parameters
    a, b = sympy.symbols(r"a b")

    sympy_equations = [
        sympy.Eq(H(t).diff(t), - (a + b) * H(t)),
        sympy.Eq(D(t).diff(t), a * H(t)),
        sympy.Eq(R(t).diff(t), b * H(t)),
    ]

    tm = template_model_from_sympy_odes(sympy_equations)
    assert set(tm.parameters) == {'a', 'b'}
    assert len(tm.templates) == 2
    assert {t.type for t in tm.templates} == {'NaturalConversion'}
    # H to R
    hr = [t for t in tm.templates if t.outcome.name == 'R'][0]
    assert hr.subject.name == 'H'
    # H to D
    hd = [t for t in tm.templates if t.outcome.name == 'D'][0]
    assert hd.subject.name == 'H'


def test_branching_implicit():
    # Define time variable
    t = sympy.symbols(r"t")

    # Define the time-dependent variables
    S, I, R, V = sympy.symbols(r"S I R V", cls=sympy.Function)

    # Define the parameters
    b, k, g = sympy.symbols(r"b k g")

    sympy_equations = [
        sympy.Eq(S(t).diff(t), -b*I(t)*S(t)),
        sympy.Eq(I(t).diff(t), b*(I(t)*S(t)) - g*I(t)),
        sympy.Eq(R(t).diff(t), k*(g*I(t))),
        sympy.Eq(V(t).diff(t), (g*I(t))*(1 - k)),
    ]

    tm = template_model_from_sympy_odes(sympy_equations)

    assert len(tm.templates) == 3

    infection = [t for t in tm.templates
                 if t.type == 'ControlledConversion'][0]
    assert infection.subject.name == 'S'
    assert infection.outcome.name == 'I'
    assert infection.controller.name == 'I'
    assert sympy_eq(infection.rate_law.args[0],
        sympy.Symbol('b') * sympy.Symbol('S') * sympy.Symbol('I'))

    recovery = [t for t in tm.templates
                if t.type == 'NaturalConversion'
                and t.outcome.name == 'R'][0]
    assert recovery.subject.name == 'I'
    assert sympy_eq(recovery.rate_law.args[0],
        sympy.Symbol('k') * sympy.Symbol('g') * sympy.Symbol('I'))

    vtransition = [t for t in tm.templates
                   if t.type == 'NaturalConversion'
                   and t.outcome.name == 'V'][0]
    assert vtransition.subject.name == 'I'
    assert sympy_eq(vtransition.rate_law.args[0],
           (1 - sympy.Symbol('k')) * sympy.Symbol('g') * sympy.Symbol('I'))


def test_no_duplicate_templates():
    # Define time variable
    t = symbols("t")

    # Define time-dependent variables
    S, E, I, R, D, C = symbols("S E I R D C", cls=Function)

    # Define constant parameters
    beta, sigma, gamma, alpha, lambda_, N = symbols("beta sigma gamma alpha lambda N")

    # Define the equations
    equation_output = [
        Eq(S(t).diff(t), (-beta * S(t) / N * I(t)).expand()),
        Eq(E(t).diff(t), (beta * S(t) / N * I(t) - sigma * E(t)).expand()),
        Eq(I(t).diff(t), (sigma * E(t) - gamma * I(t)).expand()),
        Eq(R(t).diff(t), ((1 - alpha) * gamma * I(t)).expand()),
        Eq(D(t).diff(t), (alpha * gamma * I(t)).expand()),
        Eq(C(t).diff(t), (lambda_ * gamma * I(t)).expand())
    ]
    tm = template_model_from_sympy_odes(equation_output)
    assert sum('lambda' in str(t.rate_law) for t in tm.templates) == 1


def test_negative_term():
    # Define time variable
    t = symbols("t")

    # Define time-dependent variables
    S = symbols("S", cls=Function)

    # Define constant parameters
    mu = symbols("mu")

    # Define the equations
    equation_output = [
        Eq(S(t).diff(t), -mu * S(t)),
    ]
    tm = template_model_from_sympy_odes(equation_output)
    assert tm.templates[0].rate_law.args[0] == Symbol('mu') * Symbol('S')


def test_ambiguous_edges():
    import sympy

    # Define time variable
    t = sympy.symbols("t")

    # Define time-dependent variables
    A, B, C, D = sympy.symbols("A B C D", cls=sympy.Function)

    # Define the system of ODEs
    odes = [
        sympy.Eq(A(t).diff(t), - A(t) * B(t)),
        sympy.Eq(B(t).diff(t), - A(t) * B(t)),
        sympy.Eq(C(t).diff(t), A(t) * B(t)),
        sympy.Eq(D(t).diff(t), A(t) * B(t))
    ]
    tm = template_model_from_sympy_odes(odes)

    # Make sure we resolve the ambiguity in some way, without
    # duplicating templates
    assert len(tm.templates) == 2
    assert all(t.type == 'ControlledConversion' for t in tm.templates)
    assert set(t.subject.name for t in tm.templates) == {'A', 'B'}
    assert set(t.outcome.name for t in tm.templates) == {'C', 'D'}


def test_large_model():
    import sympy

    # Define time variable
    t = sympy.symbols("t")

    # Define time-dependent variables
    S, V_c, E_c, A_c, I_c, H_c, R_c = sympy.symbols("S V_c E_c A_c I_c H_c R_c", cls=sympy.Function)
    V_f, E_f, I_f, R_f = sympy.symbols("V_f E_f I_f R_f", cls=sympy.Function)
    V_c_f, E_c_f, I_c_f, R_c_f = sympy.symbols("V_c_f E_c_f I_c_f R_c_f", cls=sympy.Function)

    # Define constant parameters
    pi, kappa_c, kappa_f, kappa_c_f = sympy.symbols("pi kappa_c kappa_f kappa_c_f")
    omega_c, omega_f, omega_c_f = sympy.symbols("omega_c omega_f omega_c_f")
    nu, mu, lambd = sympy.symbols("nu_c mu lambda")
    epsilon_c, epsilon_f, epsilon_c_f = sympy.symbols("epsilon_c epsilon_f epsilon_c_f")
    sigma_c, psi_s, psi_a = sympy.symbols("sigma_c psi_s psi_a")
    delta_c, theta_c, phi_f = sympy.symbols("delta_c theta_c phi_f")
    tau_c, gamma_c = sympy.symbols("tau_c gamma_c")
    kappa_c, kappa_f, kappa_c_f = sympy.symbols("kappa_c kappa_f kappa_c_f")
    nu_c, nu_f, nu_c_f = sympy.symbols("nu_c nu_f nu_c_f")
    sigma_f, gamma_f, delta_f, phi_c = sympy.symbols("sigma_f gamma_f delta_f phi_c")
    sigma_c_f, gamma_c_f, delta_c_f = sympy.symbols("sigma_c_f gamma_c_f delta_c_f")
    N = sympy.symbols("N")

    beta_c, eta_A, eta_H, beta_f, beta_c_f, beta_f_c = sympy.symbols("beta_c eta_A eta_H beta_f beta_c_f beta_f_c")

    # Define lambda terms
    lambda_c = (beta_c * eta_A * A_c(t) + eta_H * H_c(t) + I_c(t)) / N
    lambda_f = (beta_f * I_f(t)) / N
    lambda_c_f = (beta_c_f * I_c_f(t)) / N
    lambda_f_c = (beta_f_c * I_c_f(t)) / N

    # Define system of equations
    equations = [
        sympy.Eq(S(t).diff(t), (
                pi + kappa_c * R_c(t) + kappa_f * R_f(t) + kappa_c_f * R_c_f(t) + omega_c * V_c(t) + omega_f * V_f(
            t) + omega_c_f * V_c_f(t) - (nu + mu + lambd) * S(t)).expand()),
        sympy.Eq(V_c(t).diff(t), (nu_c * S(t) - epsilon_c * lambd * V_c(t) - (omega_c + mu) * V_c(t)).expand()),
        sympy.Eq(E_c(t).diff(t), (
                (lambda_c + lambda_c_f) * S(t) + epsilon_c * (lambda_c + lambda_c_f) * V_c(t) + epsilon_f * (
                lambda_c + lambda_c_f) * V_f(t) - (sigma_c * psi_s + sigma_c * psi_a + mu) * E_c(t)).expand()),
        sympy.Eq(A_c(t).diff(t),
                 (sigma_c * psi_a * E_c(t) - (mu + delta_c + theta_c + phi_f * lambda_f) * A_c(t)).expand()),
        sympy.Eq(I_c(t).diff(t),
                 (sigma_c * psi_s * E_c(t) - tau_c * I_c(t) - (mu + delta_c + phi_f * lambda_f) * I_c(t)).expand()),
        sympy.Eq(H_c(t).diff(t), (tau_c * I_c(t) - (mu + delta_c + gamma_c + phi_f * lambda_f) * H_c(t)).expand()),
        sympy.Eq(R_c(t).diff(t), (theta_c * A_c(t) + gamma_c * H_c(t) - (kappa_c + mu) * R_c(t)).expand()),
        sympy.Eq(V_f(t).diff(t), (nu_f * S(t) - epsilon_f * lambd * V_f(t) - (omega_f + mu) * V_f(t)).expand()),
        sympy.Eq(E_f(t).diff(t), (
                (lambda_f + lambda_f_c) * S(t) + epsilon_f * (lambda_f + lambda_f_c) * V_f(t) + epsilon_c * (
                lambda_f + lambda_f_c) * V_c(t) - (sigma_f + mu) * E_f(t)).expand()),
        sympy.Eq(I_f(t).diff(t), (sigma_f * E_f(t) - (gamma_f + mu + delta_f + phi_c * lambda_c) * I_f(t)).expand()),
        sympy.Eq(R_f(t).diff(t), (gamma_f * I_f(t) - (kappa_f + mu) * R_f(t)).expand()),
        sympy.Eq(V_c_f(t).diff(t),
                 (nu_c_f * S(t) - epsilon_c_f * lambd * V_c_f(t) - (omega_c_f + mu) * V_c_f(t)).expand()),
        sympy.Eq(E_c_f(t).diff(t), ((A_c(t) + I_c(t) + H_c(t)) * phi_f * lambda_f + phi_c * lambda_c * I_f(t) - (
                sigma_c_f + mu) * E_c_f(t)).expand()),
        sympy.Eq(I_c_f(t).diff(t), (sigma_c_f * E_c_f(t) - (gamma_c_f + mu + delta_c_f) * I_c_f(t)).expand()),
        sympy.Eq(R_c_f(t).diff(t), (gamma_c_f * I_c_f(t) - (kappa_c_f + mu) * R_c_f(t)).expand())
    ]
    tm = template_model_from_sympy_odes(equations)

    assert len(tm.templates) == 67


def test_extract_static():
    # Define time variable
    t = sympy.symbols("t")

    # Define variables with time derivative to be time-dependent functions
    DP, TE, EV, PS, ASI = sympy.symbols("DP TE EV PS ASI", cls=sympy.Function)

    # Define the equations without time-derivative on the left hand side
    equation_output = [
        sympy.Eq(DP(t).diff(t), 0),
        sympy.Eq(TE(t).diff(t), 0),
        sympy.Eq(EV(t).diff(t), 0),
        sympy.Eq(PS(t).diff(t), 0),
        sympy.Eq(ASI(t).diff(t), 0),
    ]

    tm = template_model_from_sympy_odes(equation_output)

    assert all(isinstance(t, StaticConcept) for t in tm.templates)
