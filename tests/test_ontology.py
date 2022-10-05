import unittest
from mira.dkg.askemo.api import load


class TestOntology(unittest.TestCase):
    """Test the ASKEM ontology."""

    def setUp(self) -> None:
        self.ontology = load()

    def test_ontology(self):
        """Tests for the ontology."""
        for key, data in self.ontology.items():
            self.assertRegex(data.id, "^\\d{7}$")
