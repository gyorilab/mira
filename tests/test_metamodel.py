"""Tests for the metamodel."""

import unittest

from mira.metamodel import Concept, ControlledConversion, NaturalConversion, Template


class TestMetaModel(unittest.TestCase):
    """A test case for the metamodel."""

    def test_controlled_conversion(self):
        """Test instantiating the controlled conversion."""
        infected = Concept(name="infected population", identifiers={"ido": "0000511"})
        susceptible = Concept(name="susceptible population", identifiers={"ido": "0000514"})
        immune = Concept(name="immune population", identifiers={"ido": "0000592"})

        t1 = ControlledConversion(
            controller=immune,
            subject=susceptible,
            outcome=infected,
        )
        self.assertEqual(infected, t1.outcome)
        self.assertEqual(susceptible, t1.subject)
        self.assertEqual(immune, t1.controller)
