import numpy
import scipy.integrate
import sympy

from . import Model


class OdeModel:
    def __init__(self, model: Model):
        self.y = sympy.MatrixSymbol('y', len(model.variables), 1)
        self.p = sympy.MatrixSymbol('p', len(model.parameters), 1)
        self.vmap = {variable.key: idx for idx, variable
                     in enumerate(model.variables.values())}
        self.pmap = {parameter.key: idx for idx, parameter
                     in enumerate(model.parameters.values())}

        self.kinetics = [sympy.Add() for _ in self.y]
        for transition in model.transitions.values():
            rate = self.p[self.pmap[transition.rate.key]] * \
                   sympy.Mul(
                       *[self.y[self.vmap[c.key]] for c in transition.consumed])
            for c in transition.control:
                rate *= self.y[self.vmap[c.key]]
            for c in transition.consumed:
                self.kinetics[self.vmap[c.key]] -= rate
            for p in transition.produced:
                self.kinetics[self.vmap[p.key]] += rate
        self.kinetics = sympy.Matrix(self.kinetics)
        self.kinetics_lmbd = sympy.lambdify([self.y], self.kinetics)

    def set_parameters(self, params):
        for p, v in params.items():
            self.kinetics = self.kinetics.subs(self.p[self.pmap[p]], v)
        self.kinetics_lmbd = sympy.lambdify([self.y], self.kinetics)

    def get_rhs(self):
        def rhs(t, y):
            return self.kinetics_lmbd(y[:, None])
        return rhs


def simulate_ode_model(ode_model: OdeModel, initials,
                       parameters, times):
    rhs = ode_model.get_rhs()
    ode_model.set_parameters(parameters)
    solver = scipy.integrate.ode(f=rhs)
    solver.set_initial_value(initials)
    res = numpy.zeros((len(times), ode_model.y.shape[0]))
    res[0, :] = initials
    for idx, time in enumerate(times[1:]):
        res[idx + 1, :] = solver.integrate(time)
    return res

