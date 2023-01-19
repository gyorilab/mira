"""Tests for operations on template models."""

import unittest

import sympy

from mira.metamodel import Concept, ControlledConversion, \
    GroupedControlledConversion
from mira.examples.sir import cities, sir, sir_2_city
from mira.metamodel.ops import stratify, simplify_rate_law


class TestOperations(unittest.TestCase):
    """A test case for operations on template models."""

    def test_stratify(self):
        """Test stratifying a template model by labels."""
        actual = stratify(sir, key="city", strata=cities)
        self.assertEqual(
            {template.get_key() for template in sir_2_city.templates},
            {template.get_key() for template in actual.templates},
        )

    def test_simplify_rate_law(self):
        parameters = ['alpha', 'beta', 'gamma', 'delta']
        template = GroupedControlledConversion(
            controllers=[
                Concept(name='Ailing'),
                Concept(name='Diagnosed'),
                Concept(name='Infected'),
                Concept(name='Recognized')
            ],
            subject=Concept(name='Susceptible'),
            outcome=Concept(name='Infected'),
            rate_law=sympy.parse_expr('1.0*Susceptible*(Ailing*gamma + Diagnosed*beta + Infected*alpha + Recognized*delta)',
                                      local_dict={p: sympy.Symbol(p) for p in parameters})
        )
        simplified_templates = \
            simplify_rate_law(template, parameters)
        assert len(simplified_templates) == 4, simplified_templates
        assert all(isinstance(t, ControlledConversion)
                   for t in simplified_templates)