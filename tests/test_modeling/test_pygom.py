import numpy
import pytest
import sympy

from mira.examples.sir import sir_parameterized
from mira.metamodel import *
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


def test_shared_participant():
    s, i = Concept(name='S'), Concept(name='I')
    S, I, b = sympy.symbols('S I b', real=True)
    template = MultiConversion(subjects=[s, i], outcomes=[i, i],
                               rate_law=b * S * I)
    tm = TemplateModel(templates=[template],
                       parameters={'b': Parameter(name='b', value=0.1)})
    eqs = list(template_model_to_pygom(tm).ode.get_equation())
    assert eqs == [-b * I * S, b * I * S]


def test_keyword_parameter():
    template = NaturalDegradation(subject=Concept(name='X'))
    template.set_mass_action_rate_law('lambda')
    tm = TemplateModel(templates=[template],
                       parameters={'lambda': Parameter(name='lambda',
                                                       value=0.1)})
    pygom_model = template_model_to_pygom(tm)
    assert [p.ID for p in pygom_model.param_list] == ['lambda_']


def test_no_rate_law():
    template = NaturalDegradation(subject=Concept(name='X'))
    tm = TemplateModel(templates=[template])
    rate_0, X = sympy.symbols('rate_0 X', real=True)
    eqs = list(template_model_to_pygom(tm).ode.get_equation())
    assert eqs == [-rate_0 * X]


def test_initial_without_value():
    template = NaturalDegradation(subject=Concept(name='X'))
    template.set_mass_action_rate_law('k')
    tm = TemplateModel(
        templates=[template],
        parameters={'k': Parameter(name='k', value=0.1),
                    'N': Parameter(name='N')},
        initials={'X': Initial(concept=Concept(name='X'),
                               expression=sympy.Symbol('N'))}
    )
    pygom_model = template_model_to_pygom(tm)
    assert pygom_model.initial_state is None
