"""Tests for the metamodel."""

import json
import unittest

from mira.metamodel import Concept, ControlledConversion
from mira.metamodel.templates import SCHEMA_PATH, get_json_schema


class TestMetaModel(unittest.TestCase):
    """A test case for the metamodel."""
    # Set to None for full diff, remove to have default diff
    # https://docs.python.org/3/library/unittest.html#unittest.TestCase.maxDiff
    maxDiff = None

    def test_schema(self):
        """Test that the schema is up to date."""
        self.assertTrue(SCHEMA_PATH.is_file())
        self.assertEqual(
            get_json_schema(),
            json.loads(SCHEMA_PATH.read_text()),
            msg="Regenerate an updated JSON schema by running `python -m mira.metamodel.templates`",
        )

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
