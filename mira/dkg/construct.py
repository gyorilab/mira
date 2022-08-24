"""
Generate the nodes and edges file for the MIRA domain knowledge graph.

After these are generated, see the /docker folder in the repository for loading
a neo4j instance.
"""

import csv
import json
import os
import time
from collections import Counter
from operator import methodcaller
from pathlib import Path
from textwrap import dedent

import bioontologies
import bioregistry
import click
import pystow
from bioontologies import obograph
from tabulate import tabulate
from tqdm import tqdm

from mira.dkg.utils import PREFIXES

MODULE = pystow.module("mira")
DEMO_MODULE = MODULE.module("demo", "import")
EDGE_NAMES_PATH = DEMO_MODULE.join(name="relation_info.json")
HTTP_FAILURES_PATH = DEMO_MODULE.join(name="http_parse_fails.tsv")
NODES_PATH = DEMO_MODULE.join(name="nodes.tsv")
EDGES_PATH = DEMO_MODULE.join(name="edges.tsv")
OBSOLETE = {"oboinowl:ObsoleteClass", "oboinowl:ObsoleteProperty"}
EDGES_PATHS: dict[str, Path] = {
    prefix: DEMO_MODULE.join(name=f"edges_{prefix}.tsv") for prefix in PREFIXES
}
EDGE_HEADER = (
    ":START_ID",
    ":END_ID",
    ":TYPE",
    "pred:string",
    "source:string",
    "graph:string",
)
NODE_HEADER = (
    "id:ID",
    ":LABEL",
    "name:string",
    "synonyms:string[]",
    "obsolete:boolean",
    "type:string",
    "description:string",
    "xrefs:string[]",
    "alts:string[]",
)
LABELS = {"http://www.w3.org/2000/01/rdf-schema#isDefinedBy": "is defined by"}


@click.command()
@click.option("--add-xref-edges", is_flag=True)
def main(add_xref_edges: bool):
    """Generate the node and edge files."""
    if EDGE_NAMES_PATH.is_file():
        edge_names = json.loads(EDGE_NAMES_PATH.read_text())
    else:
        edge_names = {}
        for edge_prefix in ["oboinowl", "ro", "bfo", "owl", "rdfs"]:
            click.secho(
                f"Caching {bioregistry.get_name(edge_prefix)}", fg="green", bold=True
            )
            parse_results = bioontologies.get_obograph_by_prefix(edge_prefix)
            for edge_graph in parse_results.graph_document.graphs:
                edge_graph = edge_graph.standardize()
                for edge_node in edge_graph.nodes:
                    if edge_node.deprecated:
                        continue
                    if not edge_node.lbl:
                        if "http" not in edge_node.id:
                            edge_node.lbl = edge_node.id.split(":")[1]
                        elif edge_node.id in LABELS:
                            edge_node.lbl = LABELS[edge_node.id]
                        else:
                            click.secho(f"missing label for {edge_node.id}")
                            continue
                    edge_names[edge_node.id] = edge_node.lbl.strip()
        EDGE_NAMES_PATH.write_text(json.dumps(edge_names, sort_keys=True, indent=2))

    nodes = {}
    http_nodes = []
    for prefix in PREFIXES:
        edges = []

        parse_results = bioontologies.get_obograph_by_prefix(prefix)
        _graphs = parse_results.graph_document.graphs
        click.secho(
            f"{bioregistry.get_name(prefix)} ({len(_graphs)} graphs)",
            fg="green",
            bold=True,
        )

        for graph in tqdm(_graphs, unit="graph", desc=prefix):
            graph: obograph.Graph = graph.standardize(tqdm_kwargs=dict(leave=False))
            if not graph.id:
                raise ValueError(f"graph in {prefix} missing an ID")
            for node in graph.nodes:
                if node.deprecated or not node.type or not node.prefix or not node.luid:
                    continue
                try:
                    curie = node.curie
                except ValueError:
                    tqdm.write(f"error parsing {node.id}")
                    continue
                if curie not in nodes or (curie in nodes and prefix == node.prefix):
                    nodes[curie] = (
                        node.curie,
                        node.prefix,
                        node.lbl.strip('"').strip().strip('"') if node.lbl else "",
                        ";".join(synonym.val for synonym in node.synonyms),
                        "true" if node.deprecated else "false",
                        node.type.lower(),
                        (node.definition or "")
                        .replace('"', "")
                        .replace("\n", " ")
                        .replace("  ", " "),
                        ";".join(xref.curie for xref in node.xrefs if xref.prefix),
                        ";".join(node.alternative_ids),
                    )

                if node.replaced_by:
                    edges.append(
                        (
                            node.replaced_by,
                            node.curie,
                            "replaced_by",
                            "replaced_by",
                            prefix,
                            graph.id,
                        )
                    )
                    if node.replaced_by not in nodes:
                        nodes[node.replaced_by] = (
                            node.replaced_by,
                            node.replaced_by.split(":", 1)[0],
                            "",  # label
                            "",  # synonyms
                            "true",  # deprecated
                            "CLASS",  # type
                            "",  # definition
                        )

                if add_xref_edges:
                    for xref in node.xrefs:
                        try:
                            xref_curie = xref.curie
                        except ValueError:
                            continue
                        edges.append(
                            (
                                node.curie,
                                xref.curie,
                                "xref",
                                "xref",
                                prefix,
                                graph.id,
                            )
                        )
                        if xref_curie not in nodes:
                            nodes[xref_curie] = (
                                xref.curie,
                                xref.prefix,
                                "",  # label
                                "",  # synonyms
                                "false",  # deprecated
                                "CLASS",  # type
                                "",  # definition
                            )

            counter = Counter(
                node.prefix for node in graph.nodes if node.type != "PROPERTY"
            )
            print(
                tabulate(
                    [
                        (k, count, bioregistry.get_name(k) if k is not None else "")
                        for k, count in counter.most_common()
                    ],
                    headers=["prefix", "count", "name"],
                    tablefmt="github",
                )
            )

            http_nodes.extend(
                node.id for node in graph.nodes if node.id.startswith("http")
            )

            edges.extend(
                (
                    edge.sub,
                    edge.obj,
                    edge_names[edge.pred].lower().replace(" ", "_")
                    if edge.pred in edge_names
                    else nodes[edge.pred][2].lower().replace(" ", "_")
                    if edge.pred in nodes
                    else edge.pred,
                    edge.pred,
                    prefix,
                    graph.id,
                )
                for edge in tqdm(
                    sorted(graph.edges, key=methodcaller("as_tuple")),
                    unit="edge",
                    unit_scale=True,
                )
                if edge.obj not in OBSOLETE
            )

        edges_path = EDGES_PATHS[prefix]
        with edges_path.open("w") as file:
            writer = csv.writer(file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(EDGE_HEADER)
            writer.writerows(edges)
        print("output edges to", edges_path)

    with NODES_PATH.open("w") as file:
        writer = csv.writer(file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(NODE_HEADER)
        writer.writerows(
            (
                node
                for _curie, node in tqdm(
                    sorted(nodes.items()), unit="node", unit_scale=True
                )
            )
        )
    print("output edges to", NODES_PATH)

    # CAT edge files together
    with EDGES_PATH.open("w") as file:
        writer = csv.writer(file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(EDGE_HEADER)
        for prefix, edge_path in tqdm(sorted(EDGES_PATHS.items()), desc="cat edges"):
            with edge_path.open() as edge_file:
                reader = csv.reader(
                    edge_file, delimiter="\t", quoting=csv.QUOTE_MINIMAL
                )
                _header = next(reader)
                writer.writerows(reader)

    http_counter = Counter(http_nodes)
    with HTTP_FAILURES_PATH.open("w") as file:
        for url, count in http_counter.most_common():
            print(url, count, sep="\t", file=file)


if __name__ == "__main__":
    main()
