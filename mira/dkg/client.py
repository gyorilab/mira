"""Neo4j client module."""

import itertools as itt
import logging
import os
from collections import Counter
from functools import lru_cache
from textwrap import dedent
from typing import Any, Iterable, List, Mapping, Optional, Tuple, Union

import neo4j.graph
import pystow
from gilda.grounder import Grounder
from gilda.process import normalize
from gilda.term import Term
from neo4j import GraphDatabase
from tqdm import tqdm
from typing_extensions import Literal, TypeAlias

__all__ = ["Neo4jClient"]

logger = logging.getLogger(__name__)

Node: TypeAlias = Mapping[str, Any]

TxResult: TypeAlias = Optional[List[List[Any]]]


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
        url = (
            url
            or os.environ.get("MIRA_NEO4J_URL")
            or pystow.get_config("mira", "neo4j_url")
        )
        user = (
            user
            or os.environ.get("MIRA_NEO4J_USER")
            or pystow.get_config("mira", "neo4j_user")
        )
        password = (
            password
            or os.environ.get("MIRA_NEO4J_PASSWORD")
            or pystow.get_config("mira", "neo4j_password")
        )

        # Set max_connection_lifetime to something smaller than the timeouts
        # on the server or on the way to the server. See
        # https://github.com/neo4j/neo4j-python-driver/issues/316#issuecomment-564020680
        self.driver = GraphDatabase.driver(
            url,
            auth=(user, password) if user and password else None,
            max_connection_lifetime=3 * 60,
        )
        self._session = None

    @lru_cache(maxsize=100)
    def _get_relation_label(self, curie: str) -> str:
        """"""
        r = self.get_entity(curie)
        if not r:
            return f"`{curie}`" if ":" in curie else curie
        name = r.get("name")
        if not name:
            return curie
        return name.lower().replace(" ", "_")

    @property
    def session(self) -> neo4j.Session:
        if self._session is None:
            sess = self.driver.session()
            self._session = sess
        return self._session

    def query_tx(self, query: str) -> TxResult:
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

    def query_nodes(self, query: str) -> List[Node]:
        """Run a read-only query for nodes.

        Parameters
        ----------
        query :
            The query string to be executed.

        Returns
        -------
        values :
            A list of :class:`Node` instances corresponding
            to the results of the query
        """
        return [self.neo4j_to_node(res[0]) for res in self.query_tx(query)]

    def query_relations(
        self,
        source_name: Optional[str] = None,
        source_type: Optional[str] = None,
        source_curie: Optional[str] = None,
        relation_name: Optional[str] = None,
        relation_type: Union[None, str, List[str]] = None,
        relation_min_hops: Optional[str] = None,
        relation_max_hops: Optional[str] = 1,  # set to 0 for unlimited
        relation_direction: Optional[Literal["right", "left", "both"]] = "right",
        target_name: Optional[str] = None,
        target_type: Optional[str] = None,
        target_curie: Optional[str] = None,
        full: bool = False,
        distinct: bool = False,
        limit: Optional[int] = None,
    ) -> TxResult:
        if relation_type is None:
            _relation_types = None
        elif isinstance(relation_type, str):
            _relation_types = [self._get_relation_label(relation_type)]
        elif isinstance(relation_type, list):
            _relation_types = [self._get_relation_label(r) for r in relation_type]
        else:
            raise TypeError

        match_clause = build_match_clause(
            source_name="s",
            source_type=source_type,
            source_curie=source_curie,
            relation_name="r",
            relation_type=_relation_types,
            relation_direction=relation_direction,
            relation_min_hops=relation_min_hops,
            relation_max_hops=relation_max_hops,
            target_name="t",
            target_type=target_type,
            target_curie=target_curie,
        )

        if full:
            return_clause = "s, r, t"
        elif relation_max_hops != 1:
            # see list comprehension syntax at
            # https://neo4j.com/docs/cypher-manual/current/syntax/lists/#cypher-list-comprehension
            return_clause = "s.id, [x IN r | x.pred], t.id"
        else:
            return_clause = "s.id, r.pred, t.id"

        distinct_clause = "DISTINCT " if distinct else ""
        cypher = f"MATCH {match_clause} RETURN {distinct_clause}{return_clause}"
        if limit:
            cypher = f"{cypher} LIMIT {limit}"
        return self.query_tx(cypher)

    def get_grounder_terms(self, prefix: str) -> List[Term]:
        query = dedent(
            f"""\
            MATCH (n:{prefix})
            WHERE NOT n.obsolete
            RETURN n.id, n.name, n.synonyms
        """
        )
        return [
            term
            for identifier, name, synonyms in tqdm(
                self.query_tx(query), unit="term", unit_scale=True, desc=f"{prefix}"
            )
            for term in get_terms(prefix, identifier, name, synonyms)
        ]

    def get_lexical(self):
        """Get Lexical information for all entities"""
        query = f"MATCH (n) WHERE NOT n.obsolete RETURN n.id, n.name, n.synonyms, n.description"
        return self.query_tx(query)

    def get_grounder(self, prefix: Union[str, List[str]]) -> Grounder:
        if isinstance(prefix, str):
            prefix = [prefix]
        terms = list(
            itt.chain.from_iterable(self.get_grounder_terms(p) for p in prefix)
        )
        return Grounder(terms)

    def get_node_counter(self) -> Counter:
        """Get a count of each entity type."""
        labels = [x[0] for x in self.query_tx("call db.labels();")]
        return Counter(
            {
                label: self.query_tx(f"MATCH (n:{label}) RETURN count(*)")[0][0]
                for label in labels
            }
        )

    @staticmethod
    def neo4j_to_node(neo4j_node: neo4j.graph.Node):
        props = dict(neo4j_node)
        props["labels"] = sorted(neo4j_node.labels)
        return props

    def get_entity(self, curie: str):
        """Look up an entity based on its CURIE."""
        cypher = f"""\
            MATCH (n {{ id: '{curie}'}})
            RETURN n
        """
        r = self.query_nodes(cypher)
        return r[0] if r else None


def get_terms(
    prefix: str, identifier: str, name: str, synonyms: List[str]
) -> Iterable[Term]:
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


def build_match_clause(
    *,
    source_name: Optional[str] = None,
    source_type: Optional[str] = None,
    source_curie: Optional[str] = None,
    relation_name: Optional[str] = None,
    relation_type: Optional[str] = None,
    relation_min_hops: Optional[str] = None,
    relation_max_hops: Optional[str] = 1,
    relation_direction: Optional[Literal["right", "left", "both"]] = "right",
    target_name: Optional[str] = None,
    target_type: Optional[str] = None,
    target_curie: Optional[str] = None,
) -> str:
    """Create a Cypher query from the given parameters.

    Parameters
    ----------
    source_name :
        The name of the source node. Optional.
    source_type :
        The type of the source node. Optional.
    source_curie :
        The identifier of the source node. Optional.
    relation_name :
        The name of the relation. Optional.
    relation_type :
        The type of the relation. Optional.
    relation_min_hops :
        ...
    relation_max_hops :
        ...
    relation_direction :
        The direction of the relation, one of 'left', 'right', or 'both'.
        These correspond to <-[]-, -[]->, and -[]-, respectively.
    target_name :
        The name of the target node. Optional.
    target_type :
        The type of the target node. Optional.
    target_curie :
        The identifier of the target node. Optional.

    Returns
    -------
    :
        A Cypher query as a string.
    """
    if relation_direction is None or relation_direction == "right":
        rel1, rel2 = "-", "->"
    elif relation_direction == "left":
        rel1, rel2 = "<-", "-"
    elif relation_direction == "both":
        rel1, rel2 = "-", "-"
    else:
        raise ValueError(f"Invalid relation direction: {relation_direction}")
    source = node_query(name=source_name, type=source_type, curie=source_curie)
    relation = relation_query(
        name=relation_name,
        type=relation_type,
        min_hops=relation_min_hops,
        max_hops=relation_max_hops,
    )
    target = node_query(name=target_name, type=target_type, curie=target_curie)
    return f"({source}){rel1}[{relation}]{rel2}({target})"


def node_query(
    name: Optional[str] = None,
    type: Optional[str] = None,
    curie: Optional[str] = None,
) -> str:
    """Create a Cypher node query.

    Parameters
    ----------
    name :
        The name of the node. Optional.
    type :
        The type of the node. Optional.
    curie :
        The CURIE of the node. Optional.

    Returns
    -------
    :
        A Cypher node query as a string.
    """
    if name is None:
        name = ""
    rv = name or ""
    if type:
        rv += f":{type}"
    if curie:
        if rv:
            rv += " "
        rv += f"{{id: '{curie}'}}"
    return rv


def _is_cypher_safe(s: str) -> bool:
    return ":" in s


def relation_query(
    name: Optional[str] = None,
    type: Union[None, str, List[str]] = None,
    min_hops: Optional[int] = None,
    max_hops: Optional[int] = 1,
) -> str:
    if name is None:
        name = ""
    rv = name or ""

    if type is None:
        pass
    elif isinstance(type, str):
        rv += ":"
        rv += type if _is_cypher_safe(type) else f"`{type}`"
    else:
        rv += ":"
        rv += "|".join(t if _is_cypher_safe(t) else f"`{t}`" for t in type)

    if min_hops is None:
        min_hops = 1
    if min_hops < 1:
        raise ValueError(f"minimum hops must a positive integer")

    if max_hops is None or max_hops == 0:
        range = f"*{min_hops}.."
    elif max_hops < 0:
        raise ValueError(f"maximum hops must zero or a positive integer")
    elif max_hops == 1:
        range = ""
    else:
        range = f"*{min_hops}..{max_hops}"

    return rv + range
