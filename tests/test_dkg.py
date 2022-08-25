"""Tests for the domain knowledge graph app."""

import unittest
from fastapi.testclient import TestClient
from gilda.grounder import Grounder
from mira.dkg.utils import MiraState

import pystow
import os

MIRA_NEO4J_URL = pystow.get_config("mira", "neo4j_url") or os.getenv("MIRA_NEO4J_URL")


@unittest.skipIf(MIRA_NEO4J_URL is None, reason="Missing neo4j connection configuration")
class TestDKG(unittest.TestCase):
    """Test the DKG."""

    def setUp(self) -> None:
        """Set up the test case."""
        from mira.dkg.wsgi import app

        self.client = TestClient(app)

    def test_state(self):
        """Test the app is filled up with MIRA goodness."""
        self.assertIsInstance(self.client.app.state, MiraState)
        self.assertIsInstance(self.client.app.state.grounder, Grounder)

    def test_grounding(self):
        """Test grounding."""
        response = self.client.get("/api/ground/vaccine")
        self.assertEqual(200, response.status_code, msg=response.content)
        self.assertTrue(any(
            r["prefix"] == "vo" and r["identifier"] == "0000001"
            for r in response.json()["results"]
        ))
