__all__ = ["OdeModel", "simulate_ode_model"]

from copy import deepcopy

import numpy
import scipy.integrate
import sympy

from . import Model


class OdeModel:
    """A class representing an ODE model."""
    def __init__(self, model: Model):
        self.y = sympy.MatrixSymbol('y', len(model.variables), 1)
        self.p = sympy.MatrixSymbol('p', len(model.parameters), 1)
        self.vmap = {variable.key: idx for idx, variable
                     in enumerate(model.variables.values())}
        self.pmap = {parameter.key: idx for idx, parameter
                     in enumerate(model.parameters.values())}
        concept_map = {variable.concept.name: variable.key
                       for variable in model.variables.values()}
        parameter_map = {parameter.concept.name: parameter.key
                         for parameter in model.parameters.values()
                         if not parameter.placeholder}

        self.kinetics = [sympy.Add() for _ in self.y]
        for transition in model.transitions.values():
            # Use rate if available which is a symbolic expression
            if transition.template.rate_law:
                rate = deepcopy(transition.template.rate_law.args[0])
                for symbol in rate.free_symbols:
                    sym_str = str(symbol)
                    if sym_str in concept_map:
                        rate.subs(symbol,
                                      self.y[self.vmap[concept_map[sym_str]]])
                    elif sym_str in self.pmap:
                        rate.subs(symbol,
                                      self.p[self.pmap[parameter_map[sym_str]]])
                    elif model.template_model.time and \
                            sym_str == model.template_model.time.name:
                        rate.subs(symbol, 't')
                    else:
                        assert False
            # Calculate the rate based on mass-action kinetics
            else:
                rate = self.p[self.pmap[transition.rate.key]] * sympy.Mul(
                    *[self.y[self.vmap[c.key]] for c in transition.consumed]
                )
                for c in transition.control:
                    rate *= self.y[self.vmap[c.key]]

            # Now add or substract the rate from the appropriate variables
            for c in transition.consumed:
                self.kinetics[self.vmap[c.key]] -= rate
            for p in transition.produced:
                self.kinetics[self.vmap[p.key]] += rate
        self.kinetics = sympy.Matrix(self.kinetics)
        self.kinetics_lmbd = sympy.lambdify([self.y], self.kinetics)

    def set_parameters(self, params):
        """Set the parameters of the model."""
        for p, v in params.items():
            self.kinetics = self.kinetics.subs(self.p[self.pmap[p]], v)
        self.kinetics_lmbd = sympy.lambdify([self.y], self.kinetics)

    def get_rhs(self):
        """Return the right-hand side of the ODE system."""
        def rhs(t, y):
            return self.kinetics_lmbd(y[:, None])
        return rhs

    # TODO is there a way to get the variable names in
    #  order out of this, e.g., for adding a legend to plots?


def simulate_ode_model(ode_model: OdeModel, initials,
                       parameters, times):
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

    Returns
    -------
    A two-dimensional array with the first axis being time
    and the second axis being the agents in the ODE model.
    """
    rhs = ode_model.get_rhs()
    ode_model.set_parameters(parameters)
    solver = scipy.integrate.ode(f=rhs)
    solver.set_initial_value(initials)
    res = numpy.zeros((len(times), ode_model.y.shape[0]))
    res[0, :] = initials
    for idx, time in enumerate(times[1:]):
        res[idx + 1, :] = solver.integrate(time)
    return res
