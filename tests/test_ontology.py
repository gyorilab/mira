"""Tests for the ASKEM ontology."""

import unittest
from mira.dkg.askemo.api import get_askemo_terms, EQUIVALENCE_TYPES, Term
import bioregistry


class TestOntology(unittest.TestCase):
    """Test the ASKEM ontology."""

    def setUp(self) -> None:
        """Set up the test case with a mapping from CURIEs to terms."""
        self.ontology = get_askemo_terms()
        self.manager = bioregistry.manager

    def test_ontology(self):
        """Tests for the ontology."""
        for key, term in self.ontology.items():
            self.assertIsInstance(term, Term)
            self.assertRegex(term.id, "^askemo:\\d{7}$")
            for synonym in term.synonyms or []:
                self.assertIn(synonym.type, EQUIVALENCE_TYPES)
            for xref in term.xrefs or []:
                self.assertIn(xref.type, EQUIVALENCE_TYPES)
                xref_prefix = xref.id.split(":", 1)[0]
                norm_xref_prefix = self.manager.normalize_prefix(xref_prefix)
                self.assertIsNotNone(norm_xref_prefix)
                self.assertEqual(norm_xref_prefix, xref_prefix)
        if term.physical_min:
            self.assertIsInstance(term.physical_min, float)
