"""Neo4j client module."""

import itertools as itt
import logging
import os
from collections import Counter
from functools import lru_cache
from textwrap import dedent
from typing import Any, Iterable, List, Mapping, Optional, Tuple, Union

import neo4j.graph
from gilda.grounder import Grounder
from gilda.process import normalize
from gilda.term import Term
from neo4j import GraphDatabase
from tqdm import tqdm
from typing_extensions import TypeAlias

__all__ = ["Neo4jClient"]

logger = logging.getLogger(__name__)

Node: TypeAlias = Mapping[str, Any]


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
        url = url if url else os.environ.get('MIRA_NEO4J_URL')
        user = user if user else os.environ.get('MIRA_NEO4J_USER')
        password = password if password else os.environ.get('MIRA_NEO4J_PASSWORD')

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
            return curie
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

    def get_predecessors(
        self,
        target_curie: Tuple[str, str],
        relations: Iterable[str],
        source_type: Optional[str] = None,
        target_type: Optional[str] = None,
    ) -> List[Node]:
        """Return the nodes that precede the given node via the given relation types.

        Parameters
        ----------
        target_curie :
            The target node's CURIE.
        relations :
            The relation labels to constrain to when finding predecessors.
        source_type :
            A constraint on the source type
        target_type :
            A constraint on the target type

        Returns
        -------
        predecessors
            A list of predecessor nodes.
        """
        source_name = "s"
        match = triple_query(
            source_name=source_name,
            source_type=source_type,
            relation_type="%s*1.." % "|".join(self._get_relation_label(r) for r in relations),
            target_curie=target_curie,
            target_type=target_type,
        )
        cypher = f"MATCH {match} RETURN DISTINCT {source_name}"
        return self.query_nodes(cypher)

    def get_successors(
        self,
        source_curie: Tuple[str, str],
        relations: Iterable[str],
        source_type: Optional[str] = None,
        target_type: Optional[str] = None,
    ) -> List[Node]:
        """Return the nodes that precede the given node via the given relation types.

        Parameters
        ----------
        source_curie :
            The source node's CURIE.
        relations :
            The relation labels to constrain to when finding successors.
        source_type :
            A constraint on the source type
        target_type :
            A constraint on the target type

        Returns
        -------
        predecessors
            A list of predecessor nodes.
        """
        target_name = "t"
        match = triple_query(
            source_curie=source_curie,
            source_type=source_type,
            relation_type="%s*1.." % "|".join(self._get_relation_label(r) for r in relations),
            target_name=target_name,
            target_type=target_type,
        )
        cypher = f"MATCH {match} RETURN DISTINCT {target_name}"
        return self.query_nodes(cypher)

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
            for identifier, name, synonyms in tqdm(self.query_tx(query), unit="term", unit_scale=True, desc=f"{prefix}")
            for term in get_terms(prefix, identifier, name, synonyms)
        ]

    def get_grounder(self, prefix: Union[str, List[str]]) -> Grounder:
        if isinstance(prefix, str):
            prefix = [prefix]
        terms = list(itt.chain.from_iterable(self.get_grounder_terms(p) for p in prefix))
        return Grounder(terms)

    def get_node_counter(self) -> Counter:
        """Get a count of each entity type."""
        labels = [x[0] for x in self.query_tx("call db.labels();")]
        return Counter({label: self.query_tx(f"MATCH (n:{label}) RETURN count(*)")[0][0] for label in labels})

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
        results = self.query_tx(cypher)
        if not results:
            return None
        return self.neo4j_to_node(results[0][0])

    def get_parents(self, curie: str) -> List[Node]:
        return self.get_successors(
            source_curie=curie,
            relations=["rdfs:subClassOf", "part_of"],
        )

    def is_a(self, child_curie: str, parent_curie: str) -> bool:
        """"""
        raise NotImplementedError


def get_terms(prefix: str, identifier: str, name: str, synonyms: List[str]) -> Iterable[Term]:
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


def triple_query(
    source_name: Optional[str] = None,
    source_type: Optional[str] = None,
    source_curie: Optional[str] = None,
    relation_name: Optional[str] = None,
    relation_type: Optional[str] = None,
    target_name: Optional[str] = None,
    target_type: Optional[str] = None,
    target_curie: Optional[str] = None,
    relation_direction: Optional[str] = "right",
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
    target_name :
        The name of the target node. Optional.
    target_type :
        The type of the target node. Optional.
    target_curie :
        The identifier of the target node. Optional.
    relation_direction :
        The direction of the relation, one of 'left', 'right', or 'both'.
        These correspond to <-[]-, -[]->, and -[]-, respectively.

    Returns
    -------
    :
        A Cypher query as a string.
    """
    if relation_direction == "left":
        rel1, rel2 = "<-", "-"
    elif relation_direction == "right":
        rel1, rel2 = "-", "->"
    elif relation_direction == "both":
        rel1, rel2 = "-", "-"
    else:
        raise ValueError(f"Invalid relation direction: {relation_direction}")
    source = node_query(node_name=source_name, node_type=source_type, node_curie=source_curie)
    # TODO could later make an alternate function for the relation
    relation = node_query(node_name=relation_name, node_type=relation_type)
    target = node_query(node_name=target_name, node_type=target_type, node_curie=target_curie)
    return f"({source}){rel1}[{relation}]{rel2}({target})"


def node_query(
    node_name: Optional[str] = None,
    node_type: Optional[str] = None,
    node_curie: Optional[str] = None,
) -> str:
    """Create a Cypher node query.

    Parameters
    ----------
    node_name :
        The name of the node. Optional.
    node_type :
        The type of the node. Optional.
    node_curie :
        The CURIE of the node. Optional.

    Returns
    -------
    :
        A Cypher node query as a string.
    """
    if node_name is None:
        node_name = ""
    rv = node_name or ""
    if node_type:
        rv += f":{node_type}"
    if node_curie:
        if rv:
            rv += " "
        rv += f"{{id: '{node_curie}'}}"
    return rv
