"""Tests for the triples generator."""

import unittest

from mira.examples.sir import sir
from mira.modeling.triples import TriplesGenerator, CO_OCCURS


class TestTriplesGenerator(unittest.TestCase):
    """Test the triples generator."""

    def test_sir(self):
        """This test makes sure there are connections
        between the three grounded IDO terms in the SIR model.
        """
        generator = TriplesGenerator(sir)
        expected = {
            (
                "ido:0000511",
                CO_OCCURS,
                "ido:0000592",
            ),
            (
                "ido:0000514",
                CO_OCCURS,
                "ido:0000511",
            ),
        }
        expected.update({(o, p, s) for s, p, o in expected})

        self.assertEqual(
            expected,
            set(generator.triples),
        )
