import numpy
import pytest

from mira.examples.sir import sir_parameterized
from mira.modeling import Model
from mira.modeling.ode import OdeModel, simulate_ode_model

pytest.importorskip("pygom")

from mira.modeling.pygom import template_model_to_pygom


def test_sir_matches_ode():
    times = numpy.linspace(0, 10, 11)
    pygom_model = template_model_to_pygom(sir_parameterized)
    pygom_y = pygom_model.solve_deterministic(times[1:])[0].result.y
    ode_y = simulate_ode_model(
        OdeModel(Model(sir_parameterized), initialized=True), times
    )
    assert numpy.allclose(pygom_y, ode_y[1:], rtol=1e-3)
