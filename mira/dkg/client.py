"""Neo4j client module."""

import itertools as itt
import logging
from textwrap import dedent
from typing import Any, Iterable, List, Optional, Union
from collections import Counter
import neo4j.graph
import pystow
from gilda.grounder import Grounder
from gilda.process import normalize
from gilda.term import Term
from neo4j import GraphDatabase
from tqdm import tqdm

__all__ = ["Neo4jClient"]

logger = logging.getLogger(__name__)


class Neo4jClient:
    """A client to Neo4j."""

    #: The session
    _session: Optional[neo4j.Session]

    def __init__(
        self,
        url: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        """Initialize the Neo4j client."""
        url = pystow.get_config("mira", "neo4j_url", passthrough=url, raise_on_missing=True)
        user = pystow.get_config("mira", "neo4j_user", passthrough=user)
        password = pystow.get_config("mira", "neo4j_password", passthrough=password)

        # Set max_connection_lifetime to something smaller than the timeouts
        # on the server or on the way to the server. See
        # https://github.com/neo4j/neo4j-python-driver/issues/316#issuecomment-564020680
        self.driver = GraphDatabase.driver(
            url,
            auth=(user, password) if user and password else None,
            max_connection_lifetime=3 * 60,
        )
        self._session = None

    @property
    def session(self) -> neo4j.Session:
        if self._session is None:
            sess = self.driver.session()
            self._session = sess
        return self._session

    def query_tx(self, query: str) -> Optional[List[List[Any]]]:
        tx = self.session.begin_transaction()
        try:
            res = tx.run(query)
        except Exception as e:
            logger.error(e)
            tx.close()
            return
        values = res.values()
        tx.close()
        return values

    def get_grounder_terms(self, prefix: str) -> list[Term]:
        query = dedent(
            f"""\
            MATCH (n:{prefix})
            WHERE NOT n.obsolete
            RETURN n.id, n.name, n.synonyms
        """
        )
        return [
            term
            for identifier, name, synonyms in tqdm(self.query_tx(query), unit="term", unit_scale=True, desc=f"{prefix}")
            for term in get_terms(prefix, identifier, name, synonyms)
        ]

    def get_grounder(self, prefix: Union[str, list[str]]) -> Grounder:
        if isinstance(prefix, str):
            prefix = [prefix]
        terms = list(itt.chain.from_iterable(self.get_grounder_terms(p) for p in prefix))
        return Grounder(terms)

    def get_node_counter(self) -> Counter:
        """Get a count of each entity type."""
        return Counter(
            {
                label: self.query_tx(f"MATCH (n:{label}) RETURN count(*)")[0][0]
                for label in self.query_tx("call db.labels();")[0]
            }
        )


def get_terms(prefix: str, identifier: str, name: str, synonyms: list[str]) -> Iterable[Term]:
    yield Term(
        norm_text=normalize(name),
        text=name,
        db=prefix,
        id=identifier,
        entry_name=name,
        status="name",
        source=prefix,
    )
    for synonym in synonyms or []:
        yield Term(
            norm_text=normalize(synonym),
            text=synonym,
            db=prefix,
            id=identifier,
            entry_name=name,
            status="synonym",
            source=prefix,
        )
