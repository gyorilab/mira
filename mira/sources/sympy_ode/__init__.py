import sympy
from sympy import Function, Derivative, Eq, Expr

from mira.metamodel import *


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

    # Step 1: consistency checks
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
    print('time', time_variable)

    # Step 2: determine LHS variables
    for ode in odes:
        lhs_fun = ode.lhs.args[0]
        variable_name = lhs_fun.name
        variables.append(variable_name)
    print('variables', variables)

    # Step 3: Interpret RHS equations
    consumes = {}
    produces = {}
    parameters = set()
    terms_by_key = {}
    term_effects = {}
    for lhs_variable, eq in zip(variables, odes):
        # Access the RHS
        rhs = eq.rhs
        # Break up the RHS into a sum of terms
        terms = rhs.as_ordered_terms()
        for term in terms:
            neg = is_negative(term)
            term_parameters = term.free_symbols - {time_variable}
            parameters |= term_parameters
            funcs = term.atoms(Function)
            key = (tuple(sorted([s.name for s in term.free_symbols])),
                   tuple(sorted([f.name for f in term.atoms(Function)])))
            if key not in term_effects:
                term_effects[key] = {'consumes': [], 'produces': [],
                                     'potential_controllers': set()}
            if key not in terms_by_key or not neg:
                terms_by_key[key] = term
            if neg:
                consumes[lhs_variable] = key
                term_effects[key]['consumes'].append(lhs_variable)
            else:
                produces[lhs_variable] = key
                term_effects[key]['produces'].append(lhs_variable)
            potential_controllers = {f.name for f in funcs} - {lhs_variable}
            term_effects[key]['potential_controllers'] |= potential_controllers

    params = {
        p.name: Parameter(name=p.name) for p in parameters
    }

    templates = []
    for key, effects in term_effects.items():
        controllers = effects['potential_controllers'] - set(effects['consumes'])
        print(key)
        print(terms_by_key[key])
        print(effects)
        term = terms_by_key[key]
        rate_law = term.subs({f: sympy.Symbol(f.name)
                              for f in term.atoms(Function)})
        print(rate_law)
        if len(effects['consumes']) == 1 and len(effects['produces']) == 1:
            cons = effects['consumes'][0]
            prod = effects['produces'][0]
            if cons != prod:
                cons_concept = Concept(name=cons)
                prod_concept = Concept(name=prod)
                if not controllers:
                    template = NaturalConversion(subject=cons_concept,
                                                 outcome=prod_concept,
                                                 rate_law=rate_law)
                    templates.append(template)
                elif len(controllers) == 1:
                    contr_concept = Concept(name=controllers.pop())
                    template = ControlledConversion(subject=cons_concept,
                                                    controller=contr_concept,
                                                    outcome=prod_concept,
                                                    rate_law=rate_law)
                    templates.append(template)
                else:
                    controller_concepts = [Concept(name=c) for c in controllers]
                    template = \
                        GroupedControlledConversion(subject=cons_concept,
                                                    controllers=controller_concepts,
                                                    outcome=prod_concept,
                                                    rate_law=rate_law)
                    templates.append(template)

    tm = TemplateModel(templates=templates, parameters=params)
    return tm



def is_negative(term):
    term = term.subs({s: 1 for s in term.free_symbols})
    funcs = term.atoms(Function)
    for func in funcs:
        term = sympy.diff(term, func)
    return term.is_negative