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


def test_simplify_rate_law():
    template = GroupedControlledConversion(
        controllers=[
            Concept('Ailing'),
            Concept('Diagnosed'),
            Concept('Infected'),
            Concept('Recognized')
        ],
        subject=Concept('Susceptible'),
        outcome=Concept('Infected'),
        rate_law=sympy.parse_expr('1.0*Susceptible*(Ailing*gamma + Diagnosed*beta + Infected*alpha + Recognized*delta)')
    )
    simplified_templates = \
        simplify_rate_law(template, ['alpha', 'beta', 'gamma', 'delta'])
    assert len(simplified_templates) == 4
    assert all(isinstance(t, ControlledConversion)
               for t in simplified_templates)