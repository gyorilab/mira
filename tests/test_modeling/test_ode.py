"""Tests for ODE models."""

import unittest

import numpy
import sympy

from mira.metamodel import NaturalConversion, ControlledConversion, Concept, NaturalDegradation
from mira.metamodel.template_model import TemplateModel, Initial, Parameter
from mira.modeling import Model
from mira.modeling.ode import OdeModel, simulate_ode_model


class TestODE(unittest.TestCase):
    """Test case for ODEs."""

    def test_simulate_ode(self):
        c = {
            'As_iv': Concept(name='As_iv'),
            'At_iv': Concept(name='At_iv'),
            'As_sc': Concept(name='As_sc'),
            'At_sc': Concept(name='At_sc'),
            'ALN_sc': Concept(name='ALN_sc'),
            'A_sc': Concept(name='A_sc')
        }

        As_iv, At_iv, As_sc, At_sc, ALN_sc, A_sc = sympy.symbols('As_iv At_iv As_sc At_sc ALN_sc A_sc')
        ka1, ka2, k10, k12, k21, Frc, SC_dose, IV_dose, BIO = sympy.symbols(
            'ka1 ka2 k10 k12 k21 Frc SC_dose IV_dose BIO')
        parameters = {
            'ka1': Parameter(name='ka1', value=None),
            'ka2': Parameter(name='ka2', value=None),
            'k10': Parameter(name='k10', value=None),
            'k12': Parameter(name='k12', value=None),
            'k21': Parameter(name='k21', value=None),
            'Frc': Parameter(name='Frc', value=None),
            'BIO': Parameter(name='BIO', value=None),
        }

        templates = [
            # IV dose to plasma/tissue
            NaturalConversion(subject=c['As_iv'], outcome=c['At_iv'], rate_law=As_iv * k12),
            NaturalConversion(subject=c['At_iv'], outcome=c['As_iv'], rate_law=At_iv * k21),
            NaturalDegradation(subject=c['As_iv'], rate_law=As_iv * k10),

            # SC dose to plasma/tissue
            NaturalConversion(subject=c['As_sc'], outcome=c['At_sc'], rate_law=As_sc * k12),
            NaturalConversion(subject=c['At_sc'], outcome=c['As_sc'], rate_law=At_sc * k21),
            NaturalDegradation(subject=c['As_sc'], rate_law=As_sc * k10),

            # SC dose to plasma/lymph nodes
            NaturalConversion(subject=c['ALN_sc'], outcome=c['As_sc'], rate_law=ALN_sc * ka2),
            NaturalConversion(subject=c['A_sc'], outcome=c['As_sc'], rate_law=BIO * (1 - Frc) * ka1 * A_sc),
            NaturalConversion(subject=c['A_sc'], outcome=c['ALN_sc'], rate_law=BIO * Frc * ka1 * A_sc),
        ]
        tm = TemplateModel(
            templates=templates,
            parameters=parameters,
        )
        om = OdeModel(Model(tm))

        simulate_ode_model(om,
                           [1, 1, 1, 1, 1, 1],
                           {'k12': 1, 'k21': 1, 'k10': 1, 'ka2': 1, 'BIO': 1, 'Frc': 1,
                            'ka1': 1},
                           [0, 10, 20, 30])

    def test_ode(self):
        """A simple test for ODEs, mirroring the Jupyter notebook."""
        infected = Concept(name='infected')
        recovered = Concept(name='recovered')
        susceptible = Concept(name='susceptible')
        template_model = TemplateModel(
            templates=[
                NaturalConversion(subject=infected, outcome=recovered),
                ControlledConversion(
                    subject=susceptible,
                    outcome=infected,
                    controller=infected,
                ),
            ],
            # TODO add initials here
            # initials={
            #     "infected": Initial(concept=infected, value=...),
            #     "recovered": Initial(concept=recovered, value=...),
            #     "susceptible": Initial(concept=susceptible, value=...),
            # },
        )
        model = Model(template_model)
        ode_model = OdeModel(model)
        times = numpy.linspace(0, 25, 100)

        res = simulate_ode_model(
            ode_model=ode_model,
            initials=numpy.array([0.01, 0, 0.99]),
            parameters={
                ('infected', 'recovered', 'NaturalConversion', 'rate'): 0.5,
                ('susceptible', 'infected', 'infected', 'ControlledConversion', 'rate'): 1.1
            },
            times=times
        )
        # Check that the results have 3 variables for the 3 concepts
        # and the same number of rows as number of time points
        self.assertEqual((times.shape[0], 3), res.shape)
