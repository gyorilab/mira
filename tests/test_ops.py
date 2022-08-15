"""Tests for operations on template models."""

import unittest

from mira.examples import cities, sir, sir_2_city
from mira.metamodel import NaturalConversion
from mira.modeling import TemplateModel
from mira.modeling.ops import stratify


class TestOperations(unittest.TestCase):
    """A test case for operations on template models."""

    def test_stratify(self):
        """Test stratifying a template model by labels."""
        actual = stratify(sir, key="city", strata=cities)
        self.assertEqual(
            {template.get_key() for template in sir_2_city.templates},
            {template.get_key() for template in actual.templates},
        )
