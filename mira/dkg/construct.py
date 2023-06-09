"""
Generate the nodes and edges file for the MIRA domain knowledge graph.

After these are generated, see the /docker folder in the repository for loading
a neo4j instance.

Example command for local bulk import on mac with neo4j 4.x:

.. code::

    neo4j-admin import --database=mira \
        --delimiter='TAB' \
        --force \
        --skip-duplicate-nodes=true \
        --skip-bad-relationships=true \
        --nodes ~/.data/mira/demo/import/nodes.tsv.gz \
        --relationships ~/.data/mira/demo/import/edges.tsv.gz

Then, restart the neo4j service with homebrew ``brew services neo4j restart``
"""

import csv
import gzip
import json
import pickle
import typing
from collections import Counter, defaultdict
from datetime import datetime
from operator import methodcaller
from pathlib import Path
from typing import Dict, NamedTuple, Sequence, Union, Optional

import bioontologies
import click
import pyobo
import pystow
from bioontologies import obograph
from bioregistry import manager
from pydantic import BaseModel, Field
from pyobo.struct import part_of
from pyobo.sources import ontology_resolver
from tabulate import tabulate
from tqdm.auto import tqdm
from typing_extensions import Literal

from mira.dkg.askemo import get_askemo_terms, get_askemosw_terms
from mira.dkg.models import EntityType
from mira.dkg.resources import SLIMS, get_ncbitaxon
from mira.dkg.resources.extract_ncit import get_ncit_subset
from mira.dkg.resources.probonto import get_probonto_terms
from mira.dkg.units import get_unit_terms
from mira.dkg.constants import EDGE_HEADER, NODE_HEADER
from mira.dkg.utils import PREFIXES

MODULE = pystow.module("mira")
DEMO_MODULE = MODULE.module("demo", "import")
EDGE_NAMES_PATH = DEMO_MODULE.join(name="relation_info.json")
METAREGISTRY_PATH = DEMO_MODULE.join(name="metaregistry.json")

OBSOLETE = {"oboinowl:ObsoleteClass", "oboinowl:ObsoleteProperty"}


class DKGConfig(BaseModel):
    use_case: str
    prefix: Optional[str] = None
    func: Optional[typing.Callable] = None
    iri: Optional[str] = None,
    prefixes: typing.List[str] = Field(default_factory=list)


cases: Dict[str, DKGConfig] = {
    "epi": DKGConfig(
        use_case="epi",
        prefix="askemo",
        func=get_askemo_terms,
        iri="https://github.com/indralab/mira/blob/main/mira/dkg/askemo/askemo.json",
        prefixes=PREFIXES,
    ),
    "space": DKGConfig(
        use_case="space",
        prefix="askemosw",
        func=get_askemosw_terms,
        iri="https://github.com/indralab/mira/blob/main/mira/dkg/askemo/askemosw.json",
    ),
    "eco": DKGConfig(
        use_case="eco",
        prefixes=["hgnc", "ncbitaxon", "ecocore", "probonto", "reactome"],
    ),
    "genereg": DKGConfig(
        use_case="genereg",
        prefixes=["hgnc", "go", "wikipathways", "probonto"],
    ),
}


class UseCasePaths:
    """A configuration containing the file paths for use case-specific files."""

    def __init__(self, use_case: str, config: Optional[DKGConfig] = None):
        self.use_case = use_case
        self.config = config or cases[self.use_case]
        self.askemo_prefix = self.config.prefix
        self.askemo_getter = self.config.func
        self.askemo_url = self.config.iri
        self.prefixes = self.config.prefixes

        self.module = MODULE.module(self.use_case)
        self.UNSTANDARDIZED_NODES_PATH = self.module.join(
            name="unstandardized_nodes.tsv"
        )
        self.UNSTANDARDIZED_EDGES_PATH = self.module.join(
            name="unstandardized_edges.tsv"
        )
        self.SUB_EDGE_COUNTER_PATH = self.module.join(
            name="count_subject_prefix_predicate.tsv"
        )
        self.SUB_EDGE_TARGET_COUNTER_PATH = self.module.join(
            name="count_subject_prefix_predicate_target_prefix.tsv"
        )
        self.EDGE_OBJ_COUNTER_PATH = self.module.join(
            name="count_predicate_object_prefix.tsv"
        )
        self.EDGE_COUNTER_PATH = self.module.join(name="count_predicate.tsv")
        self.NODES_PATH = self.module.join(name="nodes.tsv.gz")
        self.EDGES_PATH = self.module.join(name="edges.tsv.gz")
        self.EMBEDDINGS_PATH = self.module.join(name="embeddings.tsv.gz")

        prefixes = list(self.prefixes)
        if self.askemo_prefix:
            prefixes.append(self.askemo_prefix)
        if self.use_case == "space":
            prefixes.append("uat")
        self.EDGES_PATHS: Dict[str, Path] = {
            prefix: self.module.join("sources", name=f"edges_{prefix}.tsv")
            for prefix in prefixes
        }
        self.RDF_TTL_PATH = self.module.join(name="dkg.ttl.gz")


LABELS = {
    "http://www.w3.org/2000/01/rdf-schema#isDefinedBy": "is defined by",
    "rdf:type": "type",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#type": "type",
    # FIXME deal with these relations
    "http://purl.obolibrary.org/obo/uberon/core#proximally_connected_to": "proximally_connected_to",
    "http://purl.obolibrary.org/obo/uberon/core#extends_fibers_into": "proximally_connected_to",
    "http://purl.obolibrary.org/obo/uberon/core#channel_for": "proximally_connected_to",
    "http://purl.obolibrary.org/obo/uberon/core#distally_connected_to": "proximally_connected_to",
    "http://purl.obolibrary.org/obo/uberon/core#channels_into": "channels_into",
    "http://purl.obolibrary.org/obo/uberon/core#channels_from": "channels_from",
    "http://purl.obolibrary.org/obo/uberon/core#subdivision_of": "subdivision_of",
    "http://purl.obolibrary.org/obo/uberon/core#protects": "protects",
    "http://purl.obolibrary.org/obo/uberon/core#posteriorly_connected_to": "posteriorly_connected_to",
    "http://purl.obolibrary.org/obo/uberon/core#evolved_from": "evolved_from",
    "http://purl.obolibrary.org/obo/uberon/core#anteriorly_connected_to": "anteriorly_connected_to",
}

DEFAULT_VOCABS = [
    "oboinowl",
    "ro",
    "bfo",
    "owl",
    "rdfs",
    "bspo",
    # "gorel",
    "iao",
    # "sio",
    "omo",
    "debio",
]


class NodeInfo(NamedTuple):
    curie: str  # the id used in neo4j
    prefix: str  # the field used for neo4j labels. can contain semicolon-delimited
    label: str  # the human-readable label
    synonyms: str
    deprecated: Literal["true", "false"]  # need this for neo4j
    type: EntityType
    definition: str
    xrefs: str
    alts: str
    version: str
    property_predicates: str
    property_values: str
    xref_types: str
    synonym_types: str


@click.command()
@click.option(
    "--add-xref-edges",
    is_flag=True,
    help="Add edges for xrefs to external ontology terms",
)
@click.option(
    "--summaries",
    is_flag=True,
    help="Print summaries of nodes and edges while building",
)
@click.option("--do-upload", is_flag=True, help="Upload to S3 on completion")
@click.option("--refresh", is_flag=True, help="Refresh caches")
@click.option("--use-case", default="epi")
def main(
    add_xref_edges: bool,
    summaries: bool,
    do_upload: bool,
    refresh: bool,
    use_case: str,
):
    """Generate the node and edge files."""
    if Path(use_case).is_file():
        config = DKGConfig.parse_file(use_case)
        use_case = config.use_case
    else:
        config = None

    construct(
        use_case=use_case,
        config=config,
        refresh=refresh,
        do_upload=do_upload,
        add_xref_edges=add_xref_edges,
        summaries=summaries
    )


def construct(
    use_case: Optional[str] = None,
    config: Optional[DKGConfig] = None,
    *,
    refresh: bool = False,
    do_upload: bool = False,
    add_xref_edges: bool = False,
    summaries: bool = False,
):
    use_case_paths = UseCasePaths(use_case or config.use_case, config=config)

    if EDGE_NAMES_PATH.is_file():
        edge_names = json.loads(EDGE_NAMES_PATH.read_text())
    else:
        edge_names = {}
        for edge_prefix in DEFAULT_VOCABS:
            click.secho(f"Caching {manager.get_name(edge_prefix)}", fg="green", bold=True)
            parse_results = bioontologies.get_obograph_by_prefix(edge_prefix)
            for edge_graph in parse_results.graph_document.graphs:
                edge_graph = edge_graph.standardize()
                for edge_node in edge_graph.nodes:
                    if edge_node.deprecated or edge_node.id.startswith("_:genid"):
                        continue
                    if not edge_node.lbl:
                        if edge_node.id in LABELS:
                            edge_node.lbl = LABELS[edge_node.id]
                        elif edge_node.prefix:
                            edge_node.lbl = edge_node.luid
                        else:
                            click.secho(f"missing label for {edge_node.curie}")
                            continue
                    if not edge_node.prefix:
                        tqdm.write(f"unparsable IRI: {edge_node.id} - {edge_node.lbl}")
                        continue
                    edge_names[edge_node.curie] = edge_node.lbl.strip()
        EDGE_NAMES_PATH.write_text(json.dumps(edge_names, sort_keys=True, indent=2))

    # A mapping from CURIEs to node information tuples
    nodes: Dict[str, NodeInfo] = {}
    # A mapping from CURIEs to a set of source strings
    node_sources = defaultdict(set)
    unstandardized_nodes = []
    unstandardized_edges = []
    edge_usage_counter = Counter()
    subject_edge_usage_counter = Counter()
    subject_edge_target_usage_counter = Counter()
    edge_target_usage_counter = Counter()

    if use_case_paths.askemo_getter is not None:
        if use_case_paths.askemo_prefix is None:
            raise ValueError
        askemo_edges = []
        click.secho(f"ASKEM custom: {use_case_paths.askemo_prefix}", fg="green", bold=True)
        for term in tqdm(use_case_paths.askemo_getter().values(), unit="term"):
            property_predicates = []
            property_values = []
            if term.suggested_unit:
                property_predicates.append("suggested_unit")
                property_values.append(term.suggested_unit)
            if term.suggested_data_type:
                property_predicates.append("suggested_data_type")
                property_values.append(term.suggested_data_type)
            if term.physical_min is not None:
                property_predicates.append("physical_min")
                property_values.append(str(term.physical_min))
            if term.physical_max is not None:
                property_predicates.append("physical_max")
                property_values.append(str(term.physical_max))
            if term.typical_min is not None:
                property_predicates.append("typical_min")
                property_values.append(str(term.typical_min))
            if term.typical_max is not None:
                property_predicates.append("typical_max")
                property_values.append(str(term.typical_max))

            node_sources[term.id].add(use_case_paths.askemo_prefix)
            nodes[term.id] = NodeInfo(
                curie=term.id,
                prefix=term.prefix,
                label=term.name,
                synonyms=";".join(synonym.value for synonym in term.synonyms or []),
                deprecated="false",
                type=term.type,
                definition=term.description,
                xrefs=";".join(xref.id for xref in term.xrefs or []),
                alts="",
                version="1.0",
                property_predicates=";".join(property_predicates),
                property_values=";".join(property_values),
                xref_types=";".join(
                    xref.type or "oboinowl:hasDbXref" for xref in term.xrefs or []
                ),
                synonym_types=";".join(
                    synonym.type or "skos:exactMatch" for synonym in term.synonyms or []
                ),
            )
            for parent_curie in term.parents:
                askemo_edges.append(
                    (
                        term.id,
                        parent_curie,
                        "subclassof",
                        "rdfs:subClassOf",
                        use_case_paths.askemo_prefix,
                        use_case_paths.askemo_url,
                        "",
                    )
                )
        with use_case_paths.EDGES_PATHS[use_case_paths.askemo_prefix].open("w") as file:
            writer = csv.writer(file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(EDGE_HEADER)
            writer.writerows(askemo_edges)

    # Probability distributions
    probonto_edges = []
    for term in tqdm(get_probonto_terms(), unit="term", desc="Loading probonto"):
        curie, name, parameters = term["curie"], term["name"], term["parameters"]
        node_sources[curie].add("probonto")
        property_predicates = ["has_parameter" for _ in range(len(parameters))]
        property_values = [parameter["name"].replace("\n", " ") for parameter in parameters]
        nodes[curie] = NodeInfo(
            curie=curie,
            prefix="probonto",
            label=name,
            synonyms="",
            deprecated="false",
            type="class",
            definition="",
            xrefs=";".join(eq["curie"] for eq in term.get("equivalent", [])),
            alts="",
            version="2.5",
            property_predicates=";".join(property_predicates),
            property_values=";".join(property_values),
            xref_types=";".join("askemo:0000016" for _eq in term.get("equivalent", [])),
            synonym_types="",
        )
        # Add equivalents?
        for parameter in term.get("parameters", []):
            parameter_curie, parameter_name = parameter["curie"], parameter["name"]
            synonyms = []
            synonym_types = []
            parameter_symbol = parameter.get("symbol")
            if parameter_symbol:
                synonyms.append(parameter_symbol)
                synonym_types.append("referenced_by_latex")
            parameter_short = parameter.get("short_name")
            if parameter_short:
                synonyms.append(parameter_short)
                synonym_types.append("oboInOwl:hasExactSynonym")

            nodes[parameter_curie] = NodeInfo(
                curie=parameter_curie,
                prefix="probonto",
                label=parameter_name,
                synonyms=";".join(synonyms),
                deprecated="false",
                type="class",
                definition="",
                xrefs="",
                alts="",
                version="2.5",
                property_predicates="",
                property_values="",
                xref_types="",
                synonym_types=";".join(synonym_types),
            )
            probonto_edges.append((
                curie,
                parameter_curie,
                "has_parameter",
                "probonto:c0000062",
                "probonto",
                "https://raw.githubusercontent.com/probonto/ontology/master/probonto4ols.owl",
                "2.5",
            ))

    with use_case_paths.EDGES_PATHS["probonto"].open("w") as file:
        writer = csv.writer(file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(EDGE_HEADER)
        writer.writerows(probonto_edges)

    if use_case == "epi":
        from .resources.geonames import get_geonames_terms
        geonames_edges = []
        for term in tqdm(get_geonames_terms(), unit="term", desc="Geonames"):
            node_sources[term.curie].add("geonames")
            nodes[term.curie] = get_node_info(term, type="individual")
            for parent in term.get_relationships(part_of):
                geonames_edges.append(
                    (
                        term.curie,
                        parent.curie,
                        "part_of",
                        part_of.curie.lower(),
                        "geonames",
                        "geonames",
                        "",
                    )
                )

        with use_case_paths.EDGES_PATHS["geonames"].open("w") as file:
            writer = csv.writer(file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(EDGE_HEADER)
            writer.writerows(geonames_edges)

        # extras from NCIT
        for term in tqdm(get_ncit_subset(), unit="term", desc="NCIT"):
            node_sources[term.curie].add("ncit")
            nodes[term.curie] = get_node_info(term, type="class")
            # TODO add edges later, if needed

        for term in tqdm(get_ncbitaxon(), unit="term", desc="NCBITaxon"):
            node_sources[term.curie].add("ncbitaxon")
            nodes[term.curie] = get_node_info(term, type="class")
            # TODO add edges to source file later, if important

    if use_case == "space":
        from .resources.uat import get_uat

        uat_ontology = get_uat()
        uat_edges = []
        for term in tqdm(uat_ontology, unit="term", desc="UAT"):
            node_sources[term.curie].add(uat_ontology.ontology)
            nodes[term.curie] = NodeInfo(
                curie=term.curie,
                prefix=term.prefix,
                label=term.name,
                synonyms=";".join(synonym.name for synonym in term.synonyms or []),
                deprecated="false",
                type="class",
                definition=term.definition,
                xrefs=";".join(xref.curie for xref in term.xrefs or []),
                alts="",
                version="5.0",
                property_predicates="",
                property_values="",
                xref_types="",  # TODO
                synonym_types=";".join(
                    synonym.type or "skos:exactMatch" for synonym in term.synonyms or []
                ),
            )
            for parent in term.parents:
                uat_edges.append(
                    (
                        term.curie,
                        parent.curie,
                        "subclassof",
                        "rdfs:subClassOf",
                        uat_ontology.ontology,
                        uat_ontology.ontology,
                        "5.0",
                    )
                )
        with use_case_paths.EDGES_PATHS[uat_ontology.ontology].open("w") as file:
            writer = csv.writer(file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(EDGE_HEADER)
            writer.writerows(uat_edges)

    click.secho("Units", fg="green", bold=True)
    for wikidata_id, label, description, xrefs in tqdm(get_unit_terms(), unit="unit", desc="Units"):
        curie = f"wikidata:{wikidata_id}"
        node_sources[curie].add("wikidata")
        nodes[curie] = NodeInfo(
            curie=curie,
            prefix="wikidata;unit",
            label=label,
            synonyms="",
            deprecated="false",
            type="class",
            definition=description,
            xrefs=";".join(xrefs),
            alts="",
            version="",
            property_predicates="",
            property_values="",
            xref_types=";".join("oboinowl:hasDbXref" for _ in xrefs),
            synonym_types="",
        )

    def _get_edge_name(curie_: str, strict: bool = False) -> str:
        if curie_ in LABELS:
            return LABELS[curie_]
        elif curie_ in edge_names:
            return edge_names[curie_]
        elif curie_ in nodes:
            return nodes[curie_][2]
        elif strict:
            raise ValueError(
                f"Can not infer name for edge curie: {curie_}. Add an entry to the LABELS dictionary"
            )
        else:
            return curie_

    for prefix in use_case_paths.prefixes:
        if prefix in {"geonames", "uat", "probonto"}:  # added with custom code
            continue
        edges = []

        _results_pickle_path = DEMO_MODULE.join("parsed", name=f"{prefix}.pkl")
        if _results_pickle_path.is_file() and not refresh:
            parse_results = pickle.loads(_results_pickle_path.read_bytes())
        else:
            if prefix in SLIMS:
                parse_results = bioontologies.get_obograph_by_path(SLIMS[prefix])
            elif _pyobo_has(prefix):
                obo = pyobo.get_ontology(prefix)
                parse_results = pyobo.parse_results_from_obo(obo)
            else:
                parse_results = bioontologies.get_obograph_by_prefix(prefix)
            if parse_results.graph_document is None:
                click.secho(
                    f"{manager.get_name(prefix)} has no graph document",
                    fg="red",
                    bold=True,
                )
                _results_pickle_path.write_bytes(pickle.dumps(parse_results))
                continue

            # Standardize graphs before caching
            parse_results.graph_document.graphs = [
                graph.standardize(tqdm_kwargs=dict(leave=False))
                for graph in tqdm(
                    parse_results.graph_document.graphs,
                    unit="graph",
                    desc=f"Standardizing graphs from {prefix}",
                    leave=False,
                )
            ]
            _results_pickle_path.write_bytes(pickle.dumps(parse_results))

        _graphs = parse_results.graph_document.graphs
        click.secho(
            f"{manager.get_name(prefix)} ({len(_graphs)} graphs)", fg="green", bold=True
        )
        for graph in tqdm(_graphs, unit="graph", desc=prefix, leave=False):
            if not graph.id:
                raise ValueError(f"graph in {prefix} missing an ID")
            version = graph.version
            if version == "imports":
                version = None
            for node in graph.nodes:
                if node.deprecated or not node.prefix or not node.luid:
                    continue
                if node.id.startswith("_:gen"):  # skip blank nodes
                    continue
                try:
                    curie = node.curie
                except ValueError:
                    tqdm.write(f"error parsing {node.id}")
                    continue
                if node.curie.startswith("_:gen"):
                    continue
                node_sources[curie].add(prefix)
                if curie not in nodes or (curie in nodes and prefix == node.prefix):
                    # TODO filter out properties that are covered elsewhere
                    properties = sorted(
                        (prop.pred_curie, prop.val_curie)
                        for prop in node.properties
                        if prop.pred_prefix and prop.val_prefix
                    )
                    property_predicates, property_values = [], []
                    for pred_curie, val_curie in properties:
                        property_predicates.append(pred_curie)
                        property_values.append(val_curie)
                    nodes[curie] = NodeInfo(
                        curie=node.curie,
                        prefix=node.prefix,
                        label=node.lbl.strip('"')
                        .strip()
                        .strip('"')
                        .replace("\n", " ")
                        .replace("  ", " ")
                        if node.lbl
                        else "",
                        synonyms=";".join(synonym.val for synonym in node.synonyms),
                        deprecated="true" if node.deprecated else "false",  # type:ignore
                        # TODO better way to infer type based on hierarchy
                        #  (e.g., if rdfs:type available, consider as instance)
                        type=node.type.lower() if node.type else "unknown",  # type:ignore
                        definition=(node.definition or "")
                        .replace('"', "")
                        .replace("\n", " ")
                        .replace("  ", " "),
                        xrefs=";".join(xref.curie for xref in node.xrefs if xref.prefix),
                        alts=";".join(node.alternative_ids),
                        version=version or "",
                        property_predicates=";".join(property_predicates),
                        property_values=";".join(property_values),
                        xref_types=";".join(
                            xref.pred for xref in node.xrefs or [] if xref.prefix
                        ),
                        synonym_types=";".join(
                            synonym.pred for synonym in node.synonyms
                        ),
                    )

                if node.replaced_by:
                    edges.append(
                        (
                            node.replaced_by,
                            node.curie,
                            "replaced_by",
                            "iao:0100001",
                            prefix,
                            graph.id,
                            version or "",
                        )
                    )
                    if node.replaced_by not in nodes:
                        node_sources[node.replaced_by].add(prefix)
                        nodes[node.replaced_by] = NodeInfo(
                            node.replaced_by,
                            node.replaced_by.split(":", 1)[0],
                            label="",
                            synonyms="",
                            deprecated="true",
                            type="class",
                            definition="",
                            xrefs="",
                            alts="",
                            version="",
                            property_predicates="",
                            property_values="",
                            xref_types="",
                            synonym_types="",
                        )

                if add_xref_edges:
                    for xref in node.xrefs:
                        try:
                            xref_curie = xref.curie
                        except ValueError:
                            continue
                        if xref_curie.split(":", 1)[0] in obograph.PROVENANCE_PREFIXES:
                            # Don't add provenance information as xrefs
                            continue
                        edges.append(
                            (
                                node.curie,
                                xref.curie,
                                "xref",
                                "oboinowl:hasDbXref",
                                prefix,
                                graph.id,
                                version or "",
                            )
                        )
                        if xref_curie not in nodes:
                            node_sources[node.replaced_by].add(prefix)
                            nodes[xref_curie] = NodeInfo(
                                curie=xref.curie,
                                prefix=xref.prefix,
                                label="",
                                synonyms="",
                                deprecated="false",
                                type="class",
                                definition="",
                                xrefs="",
                                alts="",
                                version="",
                                property_predicates="",
                                property_values="",
                                xref_types="",
                                synonym_types="",
                            )

                for provenance_curie in node.get_provenance():
                    node_sources[provenance_curie].add(prefix)
                    if provenance_curie not in nodes:
                        nodes[provenance_curie] = NodeInfo(
                            curie=provenance_curie,
                            prefix=provenance_curie.split(":")[0],
                            label="",
                            synonyms="",
                            deprecated="false",
                            type="class",
                            definition="",
                            xrefs="",
                            alts="",
                            version="",
                            property_predicates="",
                            property_values="",
                            xref_types="",
                            synonym_types="",
                        )
                    edges.append(
                        (
                            node.curie,
                            provenance_curie,
                            "has_citation",
                            "debio:0000029",
                            prefix,
                            graph.id,
                            version or "",
                        )
                    )

            if summaries:
                counter = Counter(node.prefix for node in graph.nodes)
                tqdm.write(
                    "\n"
                    + tabulate(
                        [
                            (k, count, manager.get_name(k) if k is not None else "")
                            for k, count in counter.most_common()
                        ],
                        headers=["prefix", "count", "name"],
                        tablefmt="github",
                        # intfmt=",",
                    )
                )
                edge_counter = Counter(edge.pred for edge in graph.edges)
                tqdm.write(
                    "\n"
                    + tabulate(
                        [
                            (pred_curie, count, _get_edge_name(pred_curie, strict=True))
                            for pred_curie, count in edge_counter.most_common()
                        ],
                        headers=["predicate", "count", "name"],
                        tablefmt="github",
                        # intfmt=",",
                    )
                    + "\n"
                )

            unstandardized_nodes.extend(node.id for node in graph.nodes if not node.prefix)
            unstandardized_edges.extend(
                edge.pred for edge in graph.edges if edge.pred.startswith("http")
            )

            edges.extend(
                (
                    edge.sub,
                    edge.obj,
                    _get_edge_name(edge.pred).lower().replace(" ", "_").replace("-", "_"),
                    edge.pred,
                    prefix,
                    graph.id,
                    version or "",
                )
                for edge in tqdm(
                    sorted(graph.edges, key=methodcaller("as_tuple")), unit="edge", unit_scale=True
                )
                if edge.obj not in OBSOLETE
            )

        for sub, obj, pred_label, pred, *_ in edges:
            edge_target_usage_counter[pred, pred_label, obj.split(":")[0]] += 1
            subject_edge_usage_counter[sub.split(":")[0], pred, pred_label] += 1
            subject_edge_target_usage_counter[
                sub.split(":")[0], pred, pred_label, obj.split(":")[0]
            ] += 1
            edge_usage_counter[pred, pred_label] += 1

        edges_path = use_case_paths.EDGES_PATHS[prefix]
        with edges_path.open("w") as file:
            writer = csv.writer(file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(EDGE_HEADER)
            writer.writerows(edges)
        tqdm.write(f"output edges to {edges_path}")

    with gzip.open(use_case_paths.NODES_PATH, "wt") as file:
        writer = csv.writer(file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(NODE_HEADER)
        writer.writerows(
            (
                (*node, ";".join(sorted(node_sources[curie])))
                for curie, node in tqdm(sorted(nodes.items()), unit="node", unit_scale=True)
            )
        )
    tqdm.write(f"output edges to {use_case_paths.NODES_PATH}")

    # CAT edge files together
    with gzip.open(use_case_paths.EDGES_PATH, "wt") as file:
        writer = csv.writer(file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(EDGE_HEADER)
        for prefix, edge_path in tqdm(sorted(use_case_paths.EDGES_PATHS.items()), desc="cat edges"):
            with edge_path.open() as edge_file:
                reader = csv.reader(edge_file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
                _header = next(reader)
                writer.writerows(reader)

    unstandardized_nodes_counter = Counter(unstandardized_nodes)
    _write_counter(use_case_paths.UNSTANDARDIZED_NODES_PATH, unstandardized_nodes_counter, title="url")

    unstandardized_edges_counter = Counter(unstandardized_edges)
    _write_counter(use_case_paths.UNSTANDARDIZED_EDGES_PATH, unstandardized_edges_counter, title="url")

    _write_counter(
        use_case_paths.EDGE_OBJ_COUNTER_PATH,
        edge_target_usage_counter,
        unpack=True,
        title=("predicate", "predicate_label", "object_prefix"),
    )
    _write_counter(
        use_case_paths.SUB_EDGE_COUNTER_PATH,
        subject_edge_usage_counter,
        unpack=True,
        title=("subject_prefix", "predicate", "predicate_label"),
    )
    _write_counter(
        use_case_paths.SUB_EDGE_TARGET_COUNTER_PATH,
        subject_edge_target_usage_counter,
        unpack=True,
        title=("subject_prefix", "predicate", "predicate_label", "object_prefix"),
    )
    _write_counter(
        use_case_paths.EDGE_COUNTER_PATH,
        edge_usage_counter,
        unpack=True,
        title=("predicate", "predicate_label"),
    )

    if do_upload:
        upload_neo4j_s3(use_case_paths=use_case_paths)

    from .construct_rdf import _construct_rdf

    _construct_rdf(upload=do_upload, use_case_paths=use_case_paths)

    from .construct_registry import EPI_CONF_PATH, _construct_registry

    _construct_registry(
        config_path=EPI_CONF_PATH,
        output_path=METAREGISTRY_PATH,
        upload=do_upload,
    )

    from .construct_embeddings import _construct_embeddings

    _construct_embeddings(upload=do_upload, use_case_paths=use_case_paths)

    return use_case_paths


def _write_counter(
    path: Path,
    counter: Counter,
    title: Union[None, str, Sequence[str]] = None,
    unpack: bool = False,
) -> None:
    with path.open("w") as file:
        if title:
            if unpack:
                print(*title, "count", sep="\t", file=file)
            else:
                print(title, "count", sep="\t", file=file)
        for key, count in counter.most_common():
            if unpack:
                print(*key, count, sep="\t", file=file)
            else:
                print(key, count, sep="\t", file=file)


def upload_s3(
    path: Path, *, use_case: str, bucket: str = "askem-mira", s3_client=None
) -> None:
    """Upload the nodes and edges to S3."""
    if s3_client is None:
        import boto3

        s3_client = boto3.client("s3")

    today = datetime.today().strftime("%Y-%m-%d")
    # don't include a preceding or trailing slash
    key = f"dkg/{use_case}/build/{today}/"
    config = {
        # https://stackoverflow.com/questions/41904806/how-to-upload-a-file-to-s3-and-make-it-public-using-boto3
        "ACL": "public-read",
        "StorageClass": "INTELLIGENT_TIERING",
    }

    s3_client.upload_file(
        Filename=path.as_posix(),
        Bucket=bucket,
        Key=key + path.name,
        ExtraArgs=config,
    )


def upload_neo4j_s3(use_case_paths: UseCasePaths) -> None:
    """Upload the nodes and edges to S3."""
    import boto3

    s3_client = boto3.client("s3")

    paths = [
        use_case_paths.UNSTANDARDIZED_EDGES_PATH,
        use_case_paths.UNSTANDARDIZED_NODES_PATH,
        use_case_paths.NODES_PATH,
        use_case_paths.EDGES_PATH,
        use_case_paths.SUB_EDGE_COUNTER_PATH,
        use_case_paths.SUB_EDGE_TARGET_COUNTER_PATH,
        use_case_paths.EDGE_OBJ_COUNTER_PATH,
        use_case_paths.EDGE_COUNTER_PATH,
    ]
    for path in tqdm(paths):
        tqdm.write(f"uploading {path}")
        upload_s3(path=path, s3_client=s3_client, use_case=use_case_paths.use_case)


def get_node_info(term: pyobo.Term, type: EntityType = "class"):
    return NodeInfo(
        curie=term.curie,
        prefix=term.prefix,
        label=term.name,
        synonyms=";".join(synonym.name for synonym in term.synonyms or []),
        deprecated="false",
        type=type,
        definition=term.definition or "",
        xrefs="",
        alts="",
        version="",
        property_predicates="",
        property_values="",
        xref_types="",
        synonym_types=";".join(
            synonym.type or "skos:exactMatch" for synonym in term.synonyms or []
        ),
    )


def _pyobo_has(prefix: str) -> bool:
    try:
        ontology_resolver.lookup(prefix)
    except KeyError:
        return False
    return True


if __name__ == "__main__":
    main()
