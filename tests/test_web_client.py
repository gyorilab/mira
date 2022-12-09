import pytest

from requests import HTTPError

from mira.metamodel.templates import (
    RefinementClosure,
    get_dkg_refinement_closure,
)
from mira.dkg.api import RelationQuery, RelationResponse, FullRelationResponse
from mira.dkg.client import Entity
from mira.dkg.grounding import GroundResults, GroundResult
from mira.dkg.web_client import *
from mira.dkg.web_client import web_client


# Test the failsafe mechanisms in web_client
def test_web_client():
    try:
        web_client(endpoint="/relations", method="post", query_json=None)
    except Exception as exc:
        assert isinstance(exc, ValueError)
        assert "POST request to endpoint /relations requires query data" in str(
            exc
        )
    else:
        raise AssertionError(f"Expected POST request ValueError")

    # Bad method
    try:
        web_client(endpoint="/relations", method="put")
    except Exception as exc:
        assert isinstance(exc, ValueError)
        assert "Method must be one of 'get' and 'post'" in str(exc)
    else:
        raise AssertionError(f"Expected bad method ValueError")

    # Bad endpoint
    try:
        web_client(endpoint="/does_not_exist", method="get")
    except Exception as exc:
        assert isinstance(exc, HTTPError)
        assert exc.response.status_code == 404


def test_get_relations():
    res = get_relations_web(
        relations_model=RelationQuery(source_type="vo", limit=2)
    )
    assert isinstance(res, list)
    assert isinstance(res[0], RelationResponse)

    res = get_relations_web(
        relations_model=RelationQuery(source_type="vo", limit=2, full=True)
    )
    assert isinstance(res, list)
    assert isinstance(res[0], FullRelationResponse)


def test_search():
    res = search_web(term="infect")
    assert isinstance(res, list)
    assert len(res)
    assert isinstance(res[0], Entity)


def test_get_entity():
    res = get_entity_web(curie="ido:0000511")
    assert isinstance(res, Entity)
    assert res.id == "ido:0000511"


def test_ground():
    res = ground_web(text="Infected Population")
    assert isinstance(res, GroundResults)
    assert len(res.results) > 0
    assert isinstance(res.results[0], GroundResult)


def test_is_ontological_child():
    is_child = is_ontological_child_web(
        child_curie="vo:0001113",
        parent_curie="obi:0000047",
    )
    assert isinstance(is_child, bool)


@pytest.mark.slow
def test_transitive_closure():
    # Takes ~30 s locally
    tc = get_transitive_closure_web(["subclassof"])
    assert isinstance(tc, set)
    assert isinstance(list(tc)[0], tuple)
    assert len(list(tc)[0]) == 2

    # Try to make a refinement closure
    rc = RefinementClosure(transitive_closure=tc)


@pytest.mark.slow
def test_get_refinement_closure():
    # Takes ~30 s locally
    # Tests getting the refinement closure, which uses
    # get_transitive_closure_web
    rc = get_dkg_refinement_closure()
    # Check that the transitive closure
    assert isinstance(rc.transitive_closure, set)
    # Get a curie tuple
    curie_tuple = rc.transitive_closure.pop()
    assert isinstance(curie_tuple, tuple)
    # Check that tuple is a pair
    assert len(curie_tuple) == 2
    # Check that entity in tuple is 'ns:id'
    assert len(curie_tuple[0].split(":")) == 2
    assert len(curie_tuple[0].split(":")[0])
    assert len(curie_tuple[0].split(":")[1])


@pytest.mark.slow
def test_lexical():
    # Takes ~10 s locally
    res = get_lexical_web()
    assert res is not None
    assert isinstance(res, list)
    assert isinstance(res[0], dict)
    assert {"id", "name"}.issubset(res[0].keys())
