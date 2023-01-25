"""Tests for the domain knowledge graph app."""

import inspect
import os
import unittest
from typing import ClassVar

import fastapi.params
import pystow
from fastapi.testclient import TestClient
from gilda.grounder import Grounder

from mira.dkg.api import get_relations
from mira.dkg.client import AskemEntity, Entity
from mira.dkg.utils import MiraState

MIRA_NEO4J_URL = pystow.get_config("mira", "neo4j_url") or os.getenv("MIRA_NEO4J_URL")


@unittest.skipIf(not MIRA_NEO4J_URL, reason="Missing neo4j connection configuration")
class TestDKG(unittest.TestCase):
    """Test the DKG."""

    client: ClassVar[TestClient]

    @classmethod
    def setUp(cls) -> None:
        """Set up the test case."""
        from mira.dkg.wsgi import app

        cls.client = TestClient(app)
        cls.client.__enter__()

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up the test case."""
        cls.client.__exit__()

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

    def test_get_transitive_closure(self):
        """Test getting a transitive closure"""
        # NOTE: takes ~45 s to run with local Neo4j deployment
        response = self.client.get(
            "/api/transitive_closure",
            params={"relation_types": "subclassof"},
        )
        self.assertEqual(
            response.status_code, 200, msg=f"Got status {response.status_code}"
        )
        res_json = response.json()
        self.assertIsInstance(res_json, list)
        self.assertEqual(len(res_json[0]), 2)
        self.assertTrue(any(t[0].split(":")[0] == "go" for t in res_json))

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

        res3 = self.client.get("/api/search", params={
            "q": "count", "limit": 20, "offset": 5, "labels": "unit"
        })
        self.assertEqual(200, res3.status_code, msg=res3.content)
        e3 = [Entity(**e) for e in res3.json()]
        self.assertTrue(all(
            "unit" in e.labels
            for e in e3
        ))

        res4 = self.client.get("/api/search", params={
            "q": "count", "limit": 20, "offset": 5, "prefixes": "wikidata"
        })
        self.assertEqual(200, res3.status_code, msg=res4.content)
        e4 = [Entity(**e) for e in res3.json()]
        self.assertTrue(all(
            "wikidata" == e.prefix
            for e in e4
        ))

    def test_entity(self):
        """Test getting entities."""
        res = self.client.get("/api/entity/ido:0000463")
        e = Entity(**res.json())
        self.assertIsInstance(e, Entity)
        self.assertFalse(hasattr(e, "physical_min"))

        res = self.client.get("/api/entity/askemo:0000008")
        e = AskemEntity(**res.json())
        self.assertLessEqual(1, len(e.synonyms))
        self.assertTrue(
            any(
                s.value == "infectivity" and s.type == "oboInOwl:hasExactSynonym"
                for s in e.synonyms
            )
        )
        self.assertTrue(
            any(
                xref.id == "ido:0000463" and xref.type == "skos:exactMatch"
                for xref in e.xrefs
            )
        )
        self.assertEqual("float", e.suggested_data_type)
        self.assertEqual("unitless", e.suggested_unit)

        res = self.client.get("/api/entity/askemo:0000010")
        e = AskemEntity(**res.json())
        self.assertTrue(hasattr(e, "physical_min"))
        self.assertIsInstance(e.physical_min, float)
        self.assertEqual(0.0, e.physical_min)

    def test_entity_missing(self):
        """Test what happens when an entity is requested that's not in the DKG."""
        # Scenario 1: invalid prefix
        res = self.client.get("/api/entity/nope:0000008")
        self.assertEqual(404, res.status_code)

        # Scenario 2: invalid identifier
        res = self.client.get("/api/entity/askemo:ABCDE")
        self.assertEqual(404, res.status_code)

        # Scenario 3: just not in the DKG
        res = self.client.get("/api/entity/askemo:1000008")
        self.assertEqual(404, res.status_code)

    def test_search_wikidata_fallback(self):
        # first, check that without fallback, no results are returned
        res = self.client.get("/api/search", params={
            "q": "charles tapley hoyt", "wikidata_fallback": False,
        })
        self.assertEqual(200, res.status_code)
        entities = [Entity(**e) for e in res.json()]
        self.assertEqual([], entities)

        # now, turn on fallback
        res = self.client.get("/api/search", params={
            "q": "charles tapley hoyt", "wikidata_fallback": True,
        })
        self.assertEqual(200, res.status_code)
        entities = [Entity(**e) for e in res.json()]
        self.assertTrue(any(
            e.id == "wikidata:Q47475003"
            for e in entities
        ))
        self.assertEqual([], entities)

    def test_parent_query(self):
        """Test parent query."""
        res = self.client.get("/api/parents", params={
            "id": "askemo:0000008", "relation_types": "subclassof"
        })
        self.assertEqual(200, res.status_code)
        self.assertEqual(1, len(res.json()))
        self.assertEqual("askemo:0000007", res.json()[0]["id"])
