"""Neo4j client module."""

import itertools as itt
import logging
import os
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from functools import lru_cache
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple, Union

import neo4j.graph
import networkx
import pystow
import requests
from neo4j import GraphDatabase, Transaction, unit_of_work
from pydantic import BaseModel, Field, validator
from tqdm import tqdm
from typing_extensions import Literal, TypeAlias

from .models import EntityType, Synonym, Xref
from .resources import get_resource_path

if TYPE_CHECKING:
    import gilda.grounder
    import gilda.term

__all__ = ["Neo4jClient", "Entity"]

logger = logging.getLogger(__name__)

#: See documentation for query action at
#: https://www.wikidata.org/w/api.php?action=help&modules=query
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

#: Base URL for the metaregistry, used in creating links
METAREGISTRY_BASE = "http://34.230.33.149:8772"

Node: TypeAlias = Mapping[str, Any]

TxResult: TypeAlias = Optional[List[List[Any]]]


class Entity(BaseModel):
    """An entity in the domain knowledge graph."""

    id: str = Field(
        ..., title="Compact URI", description="The CURIE of the entity", example="ido:0000511"
    )
    name: Optional[str] = Field(description="The name of the entity", example="infected population")
    type: EntityType = Field(..., description="The type of the entity", example="class")
    obsolete: bool = Field(..., description="Is the entity marked obsolete?", example=False)
    description: Optional[str] = Field(
        description="The description of the entity.",
        example="An organism population whose members have an infection.",
    )
    synonyms: List[Synonym] = Field(
        default_factory=list, description="A list of string synonyms", example=[]
    )
    alts: List[str] = Field(
        title="Alternative Identifiers",
        default_factory=list,
        example=[],
        description="A list of alternative identifiers, given as CURIE strings.",
    )
    xrefs: List[Xref] = Field(
        title="Database Cross-references",
        default_factory=list,
        example=[],
        description="A list of database cross-references, given as CURIE strings.",
    )
    labels: List[str] = Field(
        default_factory=list,
        example=["ido"],
        description="A list of Neo4j labels assigned to the entity.",
    )
    properties: Dict[str, List[str]] = Field(
        default_factory=dict,
        description="A mapping of properties to their values",
        example={},
    )
    # Gets auto-populated
    link: Optional[str] = None

    @validator("link")
    def set_link(cls, value, values):
        """
        Set the value of the ``link`` field based on the value of the ``id``
        field. This gets run as a post-init hook by Pydantic

        See also:
        https://stackoverflow.com/questions/54023782/pydantic-make-field-none-in-validator-based-on-other-fields-value
        """
        curie = values["id"]
        return f"{METAREGISTRY_BASE}/{curie}"

    @property
    def prefix(self) -> str:
        """Get the prefix."""
        return self.id.split(':')[0]

    def _get_single_property(self, key: str, dtype=None):
        """Get a property value, if available.

        Parameters
        ----------
        key :
            The name of the property (either a URI, CURIE, or plain string)
        dtype :
            The datatype to cast the property into, if given. Can also be
            any callable that takes one argument and returns something.

        Returns
        -------
        A property value, if available.
        """
        values = self.properties.get(key)
        if not values:
            return None
        if len(values) != 1:
            raise ValueError(
                f"only expected 1 value for {key} in "
                f"{self.id} but got {len(values)}: {values}"
            )
        if not values[0]:
            return None
        return dtype(values[0]) if dtype else values[0]

    @classmethod
    def from_data(cls, data):
        """Create from a data dictionary as it's stored in neo4j.

        Parameters
        ----------
        data :
            Either a plain python dictionary or a :class:`neo4j.graph.Node`
            object that will get unpacked. These correspond to the structure
            of data inside the neo4j graph, and therefore have parallel lists
            representing dictionaries for properties, xrefs, and synonyms.

        Returns
        -------
        A MIRA entity
        """
        if isinstance(data, neo4j.graph.Node):
            data = dict(data.items())
        properties = defaultdict(list)
        for k, v in zip(
            data.pop("property_predicates", []),
            data.pop("property_values", []),
        ):
            properties[k].append(v)
        synonyms = []
        for value, type in zip(
            data.pop("synonyms", []),
            data.pop("synonym_types", []),
        ):
            synonyms.append(Synonym(value=value, type=type))
        xrefs = []
        for curie, type in zip(
            data.pop("xrefs", []),
            data.pop("xref_types", []),
        ):
            xrefs.append(Xref(id=curie, type=type))
        rv = cls(
            **data,
            properties=dict(properties),
            xrefs=xrefs,
            synonyms=synonyms,
        )
        if rv.prefix == "askemo":
            return rv.as_askem_entity()
        return rv

    def as_askem_entity(self):
        """Parse this term into an ASKEM Ontology-specific class."""
        if self.prefix != "askemo":
            raise ValueError(f"can only call as_askem_entity() on ASKEM ontology terms")
        if isinstance(self, AskemEntity):
            return self
        data = self.dict()
        return AskemEntity(
            **data,
            physical_min=self._get_single_property(
                "physical_min", dtype=float,
            ),
            physical_max=self._get_single_property(
                "physical_max", dtype=float,
            ),
            suggested_data_type=self._get_single_property(
                "suggested_data_type", dtype=str,
            ),
            # TODO could later extend suggested_unit to have a
            #  more sophistocated data model as well
            suggested_unit=self._get_single_property(
                "suggested_unit", dtype=str,
            ),
            typical_min=self._get_single_property("typical_min", dtype=float),
            typical_max=self._get_single_property("typical_max", dtype=float),
        )


class AskemEntity(Entity):
    """An extended entity with more ASKEM stuff loaded in."""

    # TODO @ben please write descriptions for these
    physical_min: Optional[float] = Field(description="")
    physical_max: Optional[float] = Field(description="")
    suggested_data_type: Optional[str] = Field(description="")
    suggested_unit: Optional[str] = Field(description="")
    typical_min: Optional[float] = Field(description="")
    typical_max: Optional[float] = Field(description="")


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
        # We initialize this so that the del doesn't error if some
        # exception occurs before it's initialized
        self.driver = None
        url = url or os.environ.get("MIRA_NEO4J_URL") or pystow.get_config("mira", "neo4j_url")
        user = user or os.environ.get("MIRA_NEO4J_USER") or pystow.get_config("mira", "neo4j_user")
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

    def __del__(self):
        # Safely shut down the driver as a Neo4jClient object is garbage collected
        # https://neo4j.com/docs/api/python-driver/current/api.html#driver-object-lifetime
        if self.driver is not None:
            self.driver.close()

    @lru_cache(maxsize=100)
    def _get_relation_label(self, curie: str) -> str:
        """Get the label for a relation."""
        # This works since each relation also has a corresponding entity.
        entity = self.get_entity(curie)
        if not entity:
            return f"`{curie}`" if ":" in curie else curie
        name = entity.name
        if not name:
            return curie
        return name.lower().replace(" ", "_")

    def query_tx(self, query: str, **query_params) -> Optional[TxResult]:
        # See the Session Construction section and the Session section
        # immediately following it at:
        # https://neo4j.com/docs/api/python-driver/current/api.html#session-construction
        #
        #     Session creation is a lightweight operation and sessions are
        #     not thread safe. Therefore a session should generally be
        #     short-lived, and not span multiple threads.
        #
        # To avoid a new query potentially interfering with queries already
        # in progress (or if a query has stalled or not closed properly for
        # som reason), each transaction should be performed within its own

        with self.driver.session() as session:
            # As stated here, using a context manager allows for the
            # transaction to be rolled back when an exception is raised
            # https://neo4j.com/docs/api/python-driver/current/api.html#explicit-transactions
            values = session.read_transaction(do_cypher_tx,
                                              query,
                                              **query_params)

        return values

    def create_tx(self, query: str, **query_params):
        """Run a query that creates nodes and/or relations.

        Parameters
        ----------
        query :
            The query string to be executed.
        query_params :
            The parameters to be used in the query.

        Returns
        -------
        :
            The result of the query
        """
        with self.driver.session() as session:
            return session.write_transaction(do_cypher_tx,
                                             query,
                                             **query_params)

    def create_single_property_node_index(
        self,
        index_name: str,
        label: str,
        property_name: str,
        exist_ok: bool = False
    ):
        """Create a single-property node index.

        Parameters
        ----------
        index_name :
            The name of the index to create.
        label :
            The label of the nodes to index.
        property_name :
            The node property to index.
        exist_ok :
            If True, do not raise an exception if the index already exists.
            Default: False.
        """
        if_not = " IF NOT EXISTS" if exist_ok else ""
        query = (
            f"CREATE INDEX {index_name}{if_not} "
            f"FOR (n:{label}) ON (n.{property_name})"
        )

        self.create_tx(query)

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
        return [self.neo4j_to_node(res[0]) for res in self.query_tx(query) or []]

    def query_relations(
        self,
        source_name: Optional[str] = None,
        source_type: Optional[str] = None,
        source_curie: Optional[str] = None,
        relation_name: Optional[str] = None,
        relation_type: Union[None, str, List[str]] = None,
        relation_min_hops: Optional[int] = None,
        relation_max_hops: Optional[int] = 1,  # set to 0 for unlimited
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

    def get_grounder_terms(self, prefix: str) -> List["gilda.term.Term"]:
        query = dedent(
            f"""\
            MATCH (n:{prefix})
            WHERE NOT n.obsolete and EXISTS(n.name)
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

    def get_lexical(self) -> List[Entity]:
        """Get Lexical information for all entities."""
        query = f"MATCH (n) WHERE NOT n.obsolete and EXISTS(n.name) RETURN n"
        return [Entity.from_data(n) for n, in self.query_tx(query) or []]

    def get_grounder(self, prefix: Union[str, List[str]]) -> "gilda.grounder.Grounder":
        from gilda.grounder import Grounder

        if isinstance(prefix, str):
            prefix = [prefix]
        terms = [
            term
            for term in itt.chain.from_iterable(
                self.get_grounder_terms(p) for p in tqdm(
                    prefix, desc="Caching grounding terms"
                )
            )
            if term.norm_text
        ]
        return Grounder(terms)

    def get_node_counter(self) -> Counter:
        """Get a count of each entity type."""
        labels_result = self.query_tx("call db.labels();")
        if labels_result is None:
            raise ValueError("could not look up labels")
        labels = [x[0] for x in labels_result]
        counter_data = {}
        for label in labels:
            res = self.query_tx(f"MATCH (n:`{label}`) RETURN count(*)")
            if res is not None:
                counter_data[label] = res[0][0]
        return Counter(counter_data)

    def search(
        self,
        query: str,
        limit: int = 25,
        offset: int = 0,
        prefixes: Union[None, str, Iterable[str]] = None,
        labels: Union[None, str, Iterable[str]] = None,
        wikidata_fallback: bool = False,
    ) -> List[Entity]:
        """Search nodes for a given name or synonym substring.

        Parameters
        ----------
        query :
            The query string to search (by a normalized substring search).
        limit :
            The number of results to return. Useful for pagination.
        offset :
            The offset of the entities to return. Useful for pagination.
        prefixes :
            A prefix or list of prefixes. If given, any result matching any
            of the prefixes will be retained.
        labels :
            A label or list of labels used for filtering results. If given,
            any result with any of the labels will be retained.
        wikidata_fallback :
            If true, use wikidata for searching if DKG returns no results

        Returns
        -------
        A list of entity objects that match all of the query parameters
        """
        rv = self._search(query)
        if prefixes is not None:
            prefix_set = {prefixes} if isinstance(prefixes, str) else set(prefixes)
            rv = [
                entity
                for entity in rv
                if entity.prefix in prefix_set
            ]
        if labels is not None:
            labels_set = {labels} if isinstance(labels, str) else set(labels)
            rv = [
                entity
                for entity in rv
                if any(label in labels_set for label in entity.labels)
            ]
        if not rv and wikidata_fallback:
            rv = search_wikidata(query)
        return rv[offset: offset + limit] if offset else rv[: limit]

    @lru_cache(maxsize=20)
    def _search(self, query: str) -> List[Entity]:
        """Search nodes for a given name or synonym substring.

        This function does not apply any limit or offset operations,
        but rather gets the results in full so it can be cached using
        an LRU cache then quickly paginated over later.
        """
        query_lower = query.lower().replace("-", "").replace("_", "")
        cypher = dedent(
            f"""\
            MATCH (n)
            WHERE
                EXISTS(n.name)
                AND (
                    replace(replace(toLower(n.name), '-', ''), '_', '') CONTAINS '{query_lower}'
                    OR any(
                        synonym IN n.synonyms 
                        WHERE replace(replace(toLower(synonym), '-', ''), '_', '') CONTAINS '{query_lower}'
                    )
                )
            RETURN n
        """
        )
        skip_prefixes = {"oboinowl", "rdf", "rdfs", "bfo", "cob", "ro"}
        entities = [Entity.from_data(n) for n in self.query_nodes(cypher)]
        entities = [
            entity
            for entity in entities
            if entity.name is not None and entity.prefix not in skip_prefixes
        ]
        entities = sorted(entities, key=lambda x: similarity_score(query, x))
        return entities

    @staticmethod
    def neo4j_to_node(neo4j_node: neo4j.graph.Node):
        props = dict(neo4j_node)
        props["labels"] = sorted(neo4j_node.labels)
        return props

    def get_entity(self, curie: str) -> Optional[Entity]:
        """Look up an entity based on its CURIE."""
        cypher = f"""\
            MATCH (n {{ id: '{curie}'}})
            RETURN n
        """
        r = self.query_nodes(cypher)
        if not r:
            return None
        return Entity.from_data(r[0])

    def get_transitive_closure(self, rels: Optional[List[str]] = None) -> Set[Tuple[str, str]]:
        """Return transitive closure with respect to one or more relations.

        Transitive closure is constructed as a set of pairs of node IDs
        ordered as (successor, descendant). Note that if rels are ones
        that point towards taxonomical parents (e.g., subclassof, part_of),
        then the pairs are interpreted as (taxonomical child, taxonomical
        ancestor).

        Parameters
        ----------
        rels :
             One or more relation types to traverse. If not given,
             the default DKG_REFINER_RELS are used capturing taxonomical
             parenthood relationships.

        Returns
        -------
        :
            The set of pairs constituting the transitive closure.
        """
        # Note: could not import this on top without circular import error
        if not rels:
            from mira.dkg.utils import DKG_REFINER_RELS
            rels = DKG_REFINER_RELS
        rel_type_str = '|'.join(rels)
        cypher = f"""\
            MATCH (n)-[:{rel_type_str}]->(m)
            RETURN DISTINCT n, m
        """
        logger.info(f'Finding related nodes according to {rel_type_str}...')
        r = self.query_tx(cypher)
        if not r:
            return None

        transitive_closure = set()
        g = networkx.DiGraph()
        g.add_edges_from([(n['id'], m['id']) for n, m in r])
        for node in tqdm(g, total=len(g.nodes),
                         desc=f"Building transitive closure for {rels}"):
            transitive_closure |= {
                (node, desc) for desc in networkx.descendants(g, node)
            }
        return transitive_closure

    def get_common_parents(self, curie1: str, curie2: str) -> Optional[List[Entity]]:
        """Return the direct parents of two entities."""
        from mira.dkg.utils import DKG_REFINER_RELS
        refiner_rels = '|'.join(DKG_REFINER_RELS)
        cypher = \
            f"""MATCH ({{ id: '{curie1}'}})-[:{refiner_rels}]->(p)<-[:{refiner_rels}]-({{id: '{curie2}'}})
            RETURN p"""
        res = self.query_tx(cypher)
        return [Entity(**self.neo4j_to_node(r[0])) for r in res] if res else None


# Follows example here:
# https://neo4j.com/docs/python-manual/current/session-api/#python-driver-simple-transaction-fn
# and from the docstring of neo4j.Session.read_transaction
@unit_of_work()
def do_cypher_tx(
        tx: Transaction,
        query: str,
        **query_params
) -> List[List]:
    result = tx.run(query, parameters=query_params)
    return [record.values() for record in result]


def similarity_score(query, entity: Entity) -> Tuple[float, float, float, float]:
    """Return a similarity score for a query string agains an Entity."""
    return (
        # Position in search priority list
        (search_priority_list.index(entity.id)
         if entity.id in search_priority_list
         else len(search_priority_list)),
        # The number of words in the entity
        len(entity.name.split()),
        # Similarity at the standard name level
        1 - SequenceMatcher(None, query, entity.name).ratio(),
        # Similarity among synonyms if any exist
        1 - max(SequenceMatcher(None, query, s.value).ratio()
                for s in entity.synonyms) if entity.synonyms else 1,
    )


def get_terms(
    prefix: str, identifier: str, name: str, synonyms: List[str]
) -> Iterable["gilda.term.Term"]:
    from gilda.process import normalize
    from gilda.term import Term

    norm_text = normalize(name)
    if norm_text:
        yield Term(
            norm_text=norm_text,
            text=name,
            db=prefix,
            id=identifier,
            entry_name=name,
            status="name",
            source=prefix,
        )
    for synonym in synonyms or []:
        norm_text = normalize(synonym)
        if norm_text:
            yield Term(
                norm_text=norm_text,
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
    relation_type: Union[None, str, List[str]] = None,
    relation_min_hops: Optional[int] = None,
    relation_max_hops: Optional[int] = 1,
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


def search_wikidata(text: str) -> List[Entity]:
    """Search Wikidata with the given text string."""
    payload = {
        "action": "wbsearchentities",
        "search": text,
        "language": "en",
        "format": "json",
        "limit": 50,
    }
    res = requests.get(WIKIDATA_API, params=payload)
    res.raise_for_status()
    res_json = res.json()
    results = [_process_result(r) for r in res_json["search"]]
    # TODO if "search-continue" is available, then there are more results to paginate through.
    return results


def _process_result(record: Mapping[str, Any]) -> Entity:
    return Entity(
        id=f"wikidata:{record['id']}",
        name=record["label"],
        description=record.get("description", ""),
        type="class",
        labels=["wikidata"],
        obsolete=False,
    )


def _get_search_priority_list():
    with open(get_resource_path('search_priority_list.txt'), 'r') as fh:
        return [l.strip() for l in fh.readlines()]


search_priority_list = _get_search_priority_list()

if __name__ == "__main__":
    print(repr(Neo4jClient().get_entity("ncbitaxon:10090")))
