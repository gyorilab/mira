"""Tests for the ASKEM ontology."""

import unittest

import bioregistry

from mira.dkg.askemo.api import EQUIVALENCE_TYPES, SYNONYM_TYPES, Term, get_askemo_terms


class TestOntology(unittest.TestCase):
    """Test the ASKEM ontology."""

    def setUp(self) -> None:
        """Set up the test case with a mapping from CURIEs to terms."""
        self.ontology = get_askemo_terms()
        self.manager = bioregistry.manager

    def test_ontology(self):
        """Tests for the ontology."""
        for curie, term in self.ontology.items():
            with self.subTest(curie=curie):
                self.assertIsInstance(term, Term)
                self.assertRegex(term.id, "^askemo:\\d{7}$")
                for synonym in term.synonyms or []:
                    self.assertIn(synonym.type, SYNONYM_TYPES)
                for xref in term.xrefs or []:
                    self.assertIn(xref.type, EQUIVALENCE_TYPES)
                    xref_prefix = xref.id.split(":", 1)[0]
                    norm_xref_prefix = self.manager.normalize_prefix(xref_prefix)
                    self.assertIsNotNone(norm_xref_prefix)
                    self.assertEqual(norm_xref_prefix, xref_prefix)
                if term.physical_min:
                    self.assertIsInstance(term.physical_min, float)
