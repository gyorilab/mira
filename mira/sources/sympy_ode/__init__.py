from sympy import Function, Derivative, Eq, Expr

from mira.metamodel import TemplateModel, Parameter, Concept


def template_model_from_sympy_odes(odes):
    """"
    example input: odes = [Eq(Derivative(S(t), t), -b*I(t)*S(t)),
     Eq(Derivative(E(t), t), b*I(t)*S(t) - r*E(t)),
     Eq(Derivative(I(t), t), -g*I(t) + r*E(t)),
     Eq(Derivative(R(t), t), g*I(t))]
    """

    variables = []
    parameters = {}
    time_variables = set()

    # Step 1: consistency chekcs
    for ode in odes:
        if not isinstance(ode, Eq):
            raise ValueError(f"ODE {ode} is not an equation")
        if not isinstance(ode.lhs, Derivative):
            raise ValueError(f"ODE {ode} does not have a derivative on the left-hand side")
        if not isinstance(ode.lhs.args[0], Function):
            raise ValueError(f"ODE {ode} does not have a function on the left-hand side")
        if not isinstance(ode.rhs, Expr):
            raise ValueError(f"ODE {ode} does not have an expression on the right-hand side")
        time_variables.add(ode.lhs.args[1][0])
        if len(time_variables) > 1:
            raise ValueError("Multiple time variables in the ODEs")
    time_variable = time_variables.pop()
    print(time_variable)

    # Step 2: determine LHS variables
    for ode in odes:
        lhs_fun = ode.lhs.args[0]
        variable_name = lhs_fun.name
        variables.append(variable_name)
    print(variables)

    # Step 3: Interpret RHS equations
    consumes = {}
    produces = {}
    parameters = set()
    for lhs_variable, rhs in zip(variables, odes):
        # Break up the RHS into a sum of terms
        terms = ode.rhs.as_ordered_terms()
        print(terms)
        for term in terms:
            term_parameters = term.free_symbols - {time_variable}
            parameters |= term_parameters
            funcs = term.atoms(Function)
            variable_names = [f.name for f in funcs]
            for rhs_variable in variable_name:




    return model