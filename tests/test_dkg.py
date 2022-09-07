"""Tests for the domain knowledge graph app."""

import inspect
import os
import unittest

import fastapi.params
import pystow
from fastapi.testclient import TestClient
from gilda.grounder import Grounder

from mira.dkg.api import get_relations
from mira.dkg.utils import MiraState

MIRA_NEO4J_URL = pystow.get_config("mira", "neo4j_url") or os.getenv("MIRA_NEO4J_URL")


@unittest.skipIf(not MIRA_NEO4J_URL, reason="Missing neo4j connection configuration")
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

    def test_grounding_get(self):
        """Test grounding with a get request."""
        response = self.client.get("/api/ground/vaccine")
        self.assertEqual(200, response.status_code, msg=response.content)
        self.assertTrue(
            any(
                r["prefix"] == "vo" and r["identifier"] == "0000001"
                for r in response.json()["results"]
            )
        )

    def test_grounding_post(self):
        """Test grounding with a post request."""
        response = self.client.post("/api/ground", json={"text": "vaccine"})
        self.assertEqual(200, response.status_code, msg=response.content)
        self.assertTrue(
            any(
                r["prefix"] == "vo" and r["identifier"] == "0000001"
                for r in response.json()["results"]
            )
        )

    def test_get_relations(self):
        """Test getting relations."""
        spec = inspect.signature(get_relations)
        relation_query_default = spec.parameters["relation_query"].default
        self.assertIsInstance(relation_query_default, fastapi.params.Body)

        for key, data in relation_query_default.examples.items():
            with self.subTest(key=key):
                response = self.client.post("/api/relations", json=data["value"])
                self.assertEqual(200, response.status_code, msg=response.content)
