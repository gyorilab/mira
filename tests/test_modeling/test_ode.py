"""Tests for ODE models."""

import unittest

import numpy

from mira.metamodel import NaturalConversion, ControlledConversion, Concept
from mira.metamodel.template_model import TemplateModel, Initial
from mira.modeling import Model
from mira.modeling.ode import OdeModel, simulate_ode_model


class TestODE(unittest.TestCase):
    """Test case for ODEs."""

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
