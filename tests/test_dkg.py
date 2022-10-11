"""Tests for the domain knowledge graph app."""

import inspect
import os
import unittest

import fastapi.params
import pystow
from fastapi.testclient import TestClient
from gilda.grounder import Grounder

from mira.dkg.api import get_relations
from mira.dkg.client import Entity
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

    def test_search(self):
        """Test search functionality."""
        res1 = self.client.get("/api/search", params={
            "q": "infect", "limit": 25, "offset": 0
        })
        self.assertEqual(200, res1.status_code, msg=res1.content)
        e1 = [Entity(**e) for e in res1.json()]

        res2 = self.client.get("/api/search", params={
            "q": "infect", "limit": 20, "offset": 5
        })
        self.assertEqual(200, res2.status_code, msg=res2.content)
        e2 = [Entity(**e) for e in res2.json()]
        self.assertEqual(e1[5:], e2)

    def test_entity(self):
        """Test getting entities."""
        res = self.client.get("/api/entity/askemo:0000008")
        e = Entity(**res.json())
        self.assertLessEqual(1, len(e.synonyms))
        self.assertTrue(any(s.value == "infectivity" for s in e.synonyms))
        self.assertTrue(
            any(
                xref.id == "ido:0000463" and xref.type == "skos:exactMatch"
                for xref in e.xrefs
            )
        )
        self.assertEqual("float", e.suggested_data_type)
        self.assertEqual("unitless", e.suggested_unit)

        res = self.client.get("/api/entity/askemo:0000010")
        e = Entity(**res.json())
        self.assertEqual(0.0, e.physical_min)
