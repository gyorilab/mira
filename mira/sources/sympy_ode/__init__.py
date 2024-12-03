__all__ = ['template_model_from_sympy_odes']


import sympy
from sympy import Function, Derivative, Eq, Expr

from mira.metamodel import *


def make_concept(name, data=None):
    concept_data = data.get(name, {}) if data else {}
    return Concept(name=name, **concept_data)


def make_param(name, data=None):
    param_data = data.get(name, {}) if data else {}
    return Parameter(name=name, **param_data)


def template_model_from_sympy_odes(odes, concept_data=None, param_data=None):
    """Return a TemplateModel from a set of sympy ODEs.

    Parameters
    ----------
    odes : list of sympy.Eq
        A list of sympy equations representing the ODEs.
        example input: odes = [Eq(Derivative(S(t), t), -b*I(t)*S(t)),
         Eq(Derivative(E(t), t), b*I(t)*S(t) - r*E(t)),
         Eq(Derivative(I(t), t), -g*I(t) + r*E(t)),
         Eq(Derivative(R(t), t), g*I(t))]
    concept_data : Optional[dict]
        An optional dictionary of data used when constructing
        concepts. The keys are the names of the concepts and the
        values are dictionaries of data to pass to the Concept
        constructor.
    param_data : Optional[dict]
        An optional dictionary of data used when constructing
        parameters. The keys are the names of the parameters and
        the values are dictionaries of data to pass to the Parameter
        constructor.

    Returns
    -------
    : TemplateModel
        A template model representing the ODEs.
    """
    concept_data = concept_data or {}
    param_data = param_data or {}
    variables = []
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

    # Step 2: determine LHS variables
    for ode in odes:
        lhs_fun = ode.lhs.args[0]
        variable_name = lhs_fun.name
        variables.append(variable_name)

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
            # The key contains all the parameters in the term as well
            # as all the variables in the term, plus an expression
            # representing the absolute value of the derivative of the
            # term with respect to its variables which ensures that we
            # differentiate terms with the same parameters/variables
            # but meaningfully different expressions over these.
            key = (tuple(sorted([s.name for s in term.free_symbols])),
                   tuple(sorted([f.name for f in term.atoms(Function)])),
                   abs_diff_key(term))
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
        p.name: make_param(name=p.name, data=param_data) for p in parameters
    }

    # Step 4: Create templates from the detected term effects
    templates = []
    for key, effects in term_effects.items():
        controllers = effects['potential_controllers'] - set(effects['consumes'])
        term = terms_by_key[key]
        rate_law = term.subs({f: sympy.Symbol(f.name)
                              for f in term.atoms(Function)})
        if not effects['produces']:
            if len(effects['consumes']) == 1:
                cons = effects['consumes'][0]
                if not controllers:
                    template = NaturalDegradation(subject=make_concept(cons, concept_data),
                                                  rate_law=rate_law)
                    templates.append(template)
                elif len(controllers) == 1:
                    contr_concept = make_concept(controllers.pop(), concept_data)
                    template = ControlledDegradation(subject=make_concept(cons, concept_data),
                                                     controller=contr_concept,
                                                     rate_law=rate_law)
                    templates.append(template)
                else:
                    controller_concepts = [make_concept(c, concept_data) for c in controllers]
                    template = GroupedControlledDegradation(subject=make_concept(cons, concept_data),
                                                            controllers=controller_concepts,
                                                            rate_law=rate_law)
                    templates.append(template)
        elif not effects['consumes']:
            if len(effects['produces']) == 1:
                prod = effects['produces'][0]
                if not controllers:
                    template = NaturalProduction(outcome=make_concept(prod, concept_data),
                                                 rate_law=rate_law)
                    templates.append(template)
                elif len(controllers) == 1:
                    contr_concept = make_concept(controllers.pop(), concept_data)
                    template = ControlledProduction(outcome=make_concept(prod, concept_data),
                                                    controller=contr_concept,
                                                    rate_law=rate_law)
                    templates.append(template)
                else:
                    controller_concepts = [make_concept(c, concept_data) for c in controllers]
                    template = GroupedControlledProduction(outcome=make_concept(prod,
                                                                                concept_data),
                                                           controllers=controller_concepts,
                                                           rate_law=rate_law)
                    templates.append(template)
        elif len(effects['consumes']) == 1 and len(effects['produces']) == 1:
            cons = effects['consumes'][0]
            prod = effects['produces'][0]
            if cons != prod:
                cons_concept = make_concept(cons, concept_data)
                prod_concept = make_concept(prod, concept_data)
                if not controllers:
                    template = NaturalConversion(subject=cons_concept,
                                                 outcome=prod_concept,
                                                 rate_law=rate_law)
                    templates.append(template)
                elif len(controllers) == 1:
                    contr_concept = make_concept(controllers.pop(),
                                                 concept_data)
                    template = ControlledConversion(subject=cons_concept,
                                                    controller=contr_concept,
                                                    outcome=prod_concept,
                                                    rate_law=rate_law)
                    templates.append(template)
                else:
                    controller_concepts = [make_concept(c, concept_data) for c in controllers]
                    template = \
                        GroupedControlledConversion(subject=cons_concept,
                                                    controllers=controller_concepts,
                                                    outcome=prod_concept,
                                                    rate_law=rate_law)
                    templates.append(template)

    time = Time(name=time_variable.name)
    tm = TemplateModel(templates=templates, parameters=params,
                       time=time)
    return tm


def is_negative(term):
    # Replace any parameters with 0.1, assuming positivity
    term = term.subs({s: 0.1 for s in term.free_symbols})
    # Now look at the variables appearing in the term and differentiate
    funcs = term.atoms(Function)
    for func in funcs:
        term = sympy.diff(term, func)
    # Whatever is left is the ultimate sign of the term with respect
    # to its variables
    return term.is_negative


def abs_diff_key(term):
    # Produce the absolute value of the derivative of the term
    # with respect to its variables
    funcs = term.atoms(Function)
    for func in funcs:
        term = sympy.diff(term, func)
    return abs(term)