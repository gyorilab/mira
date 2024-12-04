__all__ = ["OdeModel", "simulate_ode_model"]

from copy import deepcopy

import numpy
import scipy.integrate
import sympy

from . import Model
from ..metamodel import SympyExprStr


class OdeModel:
    """A class representing an ODE model."""

    def __init__(self, model: Model, initialized: bool):
        self.model = model
        self.y = sympy.MatrixSymbol('y', len(model.variables), 1)
        self.vmap = {variable.key: idx for idx, variable
                     in enumerate(model.variables.values())}
        self.vname_map = {idx: variable.concept.name for idx, variable
                          in enumerate(model.variables.values())}
        self.observable_map = {obs_key: idx for idx, obs_key
                               in enumerate(model.observables)}
        real_params = {k: v for k, v in model.parameters.items()
                       if not v.placeholder}
        self.p = sympy.MatrixSymbol('p', len(real_params), 1)
        self.pmap = {parameter.key: idx for idx, (pkey, parameter)
                     in enumerate(real_params.items())}
        concept_map = {variable.concept.name: variable.key
                       for variable in model.variables.values()}
        parameter_map = {parameter.concept.name: parameter.key
                         for parameter in real_params.values()}

        """Following code block is agnostic towards the case if the ODE model
        was created with parameter and initial values initialized when
        creating parameters or when calling the simulate_ode method."""
        if initialized:
            self.parameter_values = []
            self.variable_values = []
            for parameter_object in model.parameters.values():
                if not parameter_object.placeholder:
                    self.parameter_values.append(parameter_object.value)
            for variable_object in model.variables.values():
                self.variable_values.append(variable_object.data['expression'])

        self.kinetics = [sympy.Add() for _ in self.y]
        for transition in model.transitions.values():
            # Use rate if available which is a symbolic expression
            if transition.template.rate_law:
                rate = deepcopy(transition.template.rate_law.args[0])
                for symbol in rate.free_symbols:
                    sym_str = str(symbol)
                    if sym_str in concept_map:
                        rate = rate.subs(symbol,
                                         self.y[self.vmap[concept_map[sym_str]]])
                    elif sym_str in self.pmap:
                        rate = rate.subs(symbol,
                                         self.p[self.pmap[parameter_map[sym_str]]])
                    elif model.template_model.time and \
                            sym_str == model.template_model.time.name:
                        rate = rate.subs(symbol, 't')
                    else:
                        assert False
            # Calculate the rate based on mass-action kinetics
            else:
                rate = self.p[self.pmap[transition.rate.key]] * sympy.Mul(
                    *[self.y[self.vmap[c.key]] for c in transition.consumed]
                )
                for c in transition.control:
                    rate *= self.y[self.vmap[c.key]]

            # Now add or subtract the rate from the appropriate variables
            for c in transition.consumed:
                self.kinetics[self.vmap[c.key]] -= rate
            for p in transition.produced:
                self.kinetics[self.vmap[p.key]] += rate
        self.kinetics = sympy.Matrix(self.kinetics)
        self.kinetics_lmbd = sympy.lambdify([self.y], self.kinetics)

        observables = []
        for obs_name, model_obs in model.observables.items():
            expr = deepcopy(model_obs.observable.expression).args[0]
            for symbol in expr.free_symbols:
                sym_str = str(symbol)
                if sym_str in concept_map:
                    expr = expr.subs(symbol,
                                     self.y[self.vmap[concept_map[sym_str]]])
                elif sym_str in self.pmap:
                    expr = expr.subs(symbol,
                                     self.p[self.pmap[parameter_map[sym_str]]])
                elif model.template_model.time and \
                        sym_str == model.template_model.time.name:
                    expr = expr.subs(symbol, 't')
                else:
                    assert False, sym_str
            observables.append(expr)
        self.observables = sympy.Matrix(observables)
        self.observables_lmbd = sympy.lambdify([self.y], self.observables)

    def get_interpretable_kinetics(self):
        # Return kinetics but with y and p substituted
        # based on vmap and pmap
        subs = {self.y[v]: sympy.Symbol(k) if isinstance(k, str)
                else sympy.Symbol(k[0])
                for k, v in self.vmap.items()}
        subs.update({self.p[p]: sympy.Symbol(k) for k, p in self.pmap.items()})
        rhs = sympy.Matrix([
            k.subs(subs) for k in self.kinetics
        ])

        lhs = sympy.Matrix([sympy.Derivative(sympy.Symbol(self.model.variables[k].concept.name),
                                             sympy.Symbol('t')) for k, v in self.vmap.items()])

        equations = sympy.Matrix([[lhs[i], sympy.Symbol('='), rhs[i]] for i in range(len(lhs))])
        return equations

    def get_interpretable_observables(self):
        subs = {self.y[v]: sympy.Symbol(k) if isinstance(k, str) else k[0] for k, v in self.vmap.items()}
        subs.update({self.p[p]: sympy.Symbol(k) for k, p in self.pmap.items()})

        lhs = sympy.Matrix([sympy.Symbol(k) for k in self.observable_map.keys()])

        obs = sympy.Matrix([
            k.subs(subs) for k in self.observables
        ])

        equations = sympy.Matrix([[lhs[i], sympy.Symbol('='), obs[i]] for i in range(len(lhs))])
        return equations

    def plot_simulation_results(self, times, res):
        """Plot the results of a simulation.

        Parameters
        ----------
        times :
            A one-dimensional array of time values
        res :
            A two-dimensional array with the first axis being time
            and the second axis being the agents in the ODE model.
        """
        import matplotlib.pyplot as plt
        num_vars = self.y.shape[0]
        num_obs = len(self.observable_map)
        num_cols = num_vars + num_obs
        num_rows = num_cols // 4 + 1
        fig, axes = plt.subplots(num_rows, 4, figsize=(16, 18))
        for idx, ax in enumerate(axes.flat):
            if idx >= num_cols:
                ax.axis('off')
                continue
            if idx < num_vars:
                ax.plot(times, res[:, idx])
                ax.set_title(self.vname_map[idx])
            else:
                ax.plot(times, res[:, idx])
                ax.set_title(list(self.observable_map.keys())[idx - num_vars])
        plt.show()

    def set_parameters(self, params):
        """Set the parameters of the model."""
        for p, v in params.items():
            self.kinetics = self.kinetics.subs(self.p[self.pmap[p]], v)
            self.observables = self.observables.subs(self.p[self.pmap[p]], v)
        self.kinetics_lmbd = sympy.lambdify([self.y], self.kinetics)
        self.observables_lmbd = sympy.lambdify([self.y], self.observables)

    def get_rhs(self):
        """Return the right-hand side of the ODE system."""

        def rhs(t, y):
            return self.kinetics_lmbd(y[:, None])

        return rhs

    def simulate_model(self, times, initials=None,
                       parameters=None, with_observables=False):
        """Simulate the ODE model given initial conditions, parameters and a
        time span.

        Parameters
        ----------
        initials :
            A one-dimensional array describing the initial values
            for the agents in the ODE model
        parameters :
            A dictionary of keys for parameters to their values
        times :
            A one-dimensional array of time values, typically from
            a linear space like ``numpy.linspace(0, 25, 100)``
        with_observables :
            A boolean indicating whether to return the observables
            as well as the variables.

        Returns
        -------
        A two-dimensional array with the first axis being time
        and the second axis being the agents in the ODE model.
        """
        rhs = self.get_rhs()

        # If parameters and initial values for agents have already been
        # initialized before calling the simulate_ode method
        if parameters is None and initials is None:
            parameters = {}
            parameter_name_list = self.pmap.keys()
            for parameter, parameter_value in zip(parameter_name_list,
                                                  self.parameter_values):
                parameters[parameter] = parameter_value

            initials = self.variable_values
            for index, expression in enumerate(initials):
                # Only substitute if this is an expression. Once the model
                # has been simulated, this is actually a float.
                if isinstance(expression, sympy.Expr):
                    initials[index] = float(expression.subs(parameters).args[0])

        self.set_parameters(parameters)
        solver = scipy.integrate.ode(f=rhs)

        solver.set_initial_value(initials)
        num_vars = self.y.shape[0]
        num_obs = len(self.observable_map)
        num_cols = num_vars + (num_obs if with_observables else 0)
        res = numpy.zeros((len(times), num_cols))
        res[0, :num_vars] = initials
        for idx, time in enumerate(times[1:]):
            res[idx + 1, :num_vars] = solver.integrate(time)

        if with_observables:
            for tidx, t in enumerate(times):
                obs_res = \
                    self.observables_lmbd(res[tidx, :num_vars][:, None])
                for idx, val in enumerate(obs_res):
                    res[tidx, num_vars + idx] = obs_res[idx]
        return res


def simulate_ode_model(ode_model: OdeModel, times, initials=None,
                       parameters=None, with_observables=False):
    """Simulate an ODE model given initial conditions, parameters and a
    time span.

    Parameters
    ----------
    ode_model:
        An ODE model constructed from metamodel templates
    initials:
        A one-dimensional array describing the initial values
        for the agents in the ODE model
    parameters:
        A dictionary of keys for parameters to their values
    times:
        A one-dimensional array of time values, typically from
        a linear space like ``numpy.linspace(0, 25, 100)``
    with_observables:
        A boolean indicating whether to return the observables
        as well as the variables.

    Returns
    -------
    A two-dimensional array with the first axis being time
    and the second axis being the agents in the ODE model.
    """
    return ode_model.simulate_model(times, initials, parameters,
                                    with_observables)
