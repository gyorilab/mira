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
from datetime import datetime
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
UNSTANDARDIZED_NODES_PATH = DEMO_MODULE.join(name="unstandardized_nodes.tsv")
UNSTANDARDIZED_EDGES_PATH = DEMO_MODULE.join(name="unstandardized_edges.tsv")
NODES_PATH = DEMO_MODULE.join(name="nodes.tsv")
EDGES_PATH = DEMO_MODULE.join(name="edges.tsv")
OBSOLETE = {"oboinowl:ObsoleteClass", "oboinowl:ObsoleteProperty"}
EDGES_PATHS: dict[str, Path] = {
    prefix: DEMO_MODULE.join(name=f"edges_{prefix}.tsv") for prefix in PREFIXES
}
EDGE_HEADER = (":START_ID", ":END_ID", ":TYPE", "pred:string", "source:string", "graph:string")
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
]


@click.command()
@click.option("--add-xref-edges", is_flag=True)
def main(add_xref_edges: bool):
    """Generate the node and edge files."""
    if EDGE_NAMES_PATH.is_file():
        edge_names = json.loads(EDGE_NAMES_PATH.read_text())
    else:
        edge_names = {}
        for edge_prefix in DEFAULT_VOCABS:
            click.secho(f"Caching {bioregistry.get_name(edge_prefix)}", fg="green", bold=True)
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
                    edge_names[edge_node.curie] = edge_node.lbl.strip()
        EDGE_NAMES_PATH.write_text(json.dumps(edge_names, sort_keys=True, indent=2))

    nodes = {}
    unstandardized_nodes = []
    unstandardized_edges = []

    def _get_edge_name(curie_: str, strict: bool = False) -> str:
        if curie_ in edge_names:
            return edge_names[curie_]
        elif curie_ in nodes:
            return nodes[curie_][2]
        elif strict:
            return ""
        else:
            return curie_

    for prefix in PREFIXES:
        edges = []

        parse_results = bioontologies.get_obograph_by_prefix(prefix)
        _graphs = parse_results.graph_document.graphs
        click.secho(
            f"{bioregistry.get_name(prefix)} ({len(_graphs)} graphs)", fg="green", bold=True
        )

        for graph in tqdm(_graphs, unit="graph", desc=prefix):
            graph: obograph.Graph = graph.standardize(tqdm_kwargs=dict(leave=False))
            if not graph.id:
                raise ValueError(f"graph in {prefix} missing an ID")
            for node in graph.nodes:
                if node.deprecated or not node.type or not node.prefix or not node.luid:
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

            counter = Counter(node.prefix for node in graph.nodes)
            tqdm.write(
                "\n"
                + tabulate(
                    [
                        (k, count, bioregistry.get_name(k) if k is not None else "")
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
                edge.pred for edge in graph.edges if edge.pred.startswith("obo:")
            )

            edges.extend(
                (
                    edge.sub,
                    edge.obj,
                    _get_edge_name(edge.pred).lower().replace(" ", "_").replace("-", "_"),
                    edge.pred,
                    prefix,
                    graph.id,
                )
                for edge in tqdm(
                    sorted(graph.edges, key=methodcaller("as_tuple")), unit="edge", unit_scale=True
                )
                if edge.obj not in OBSOLETE
            )

        edges_path = EDGES_PATHS[prefix]
        with edges_path.open("w") as file:
            writer = csv.writer(file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(EDGE_HEADER)
            writer.writerows(edges)
        tqdm.write(f"output edges to {edges_path}")

    with NODES_PATH.open("w") as file:
        writer = csv.writer(file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(NODE_HEADER)
        writer.writerows(
            (node for _curie, node in tqdm(sorted(nodes.items()), unit="node", unit_scale=True))
        )
    tqdm.write(f"output edges to {NODES_PATH}")

    # CAT edge files together
    with EDGES_PATH.open("w") as file:
        writer = csv.writer(file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(EDGE_HEADER)
        for prefix, edge_path in tqdm(sorted(EDGES_PATHS.items()), desc="cat edges"):
            with edge_path.open() as edge_file:
                reader = csv.reader(edge_file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
                _header = next(reader)
                writer.writerows(reader)

    unstandardized_nodes_counter = Counter(unstandardized_nodes)
    with UNSTANDARDIZED_NODES_PATH.open("w") as file:
        for url, count in unstandardized_nodes_counter.most_common():
            print(url, count, sep="\t", file=file)

    unstandardized_edges_counter = Counter(unstandardized_edges)
    with UNSTANDARDIZED_EDGES_PATH.open("w") as file:
        for url, count in unstandardized_edges_counter.most_common():
            print(url, count, sep="\t", file=file)

    upload_s3()


def upload_s3(bucket: str = "askem-mira", intelligent_tiering: bool = False) -> None:
    """Upload the nodes and edges to S3."""
    import boto3

    today = datetime.today().strftime("%Y-%m-%d")
    # don't include a preceding or trailing slash
    key = f"dkg/epi/build/{today}/"
    config = {
        # https://stackoverflow.com/questions/41904806/how-to-upload-a-file-to-s3-and-make-it-public-using-boto3
        "ACL": "public-read",
    }
    if intelligent_tiering:
        config["StorageClass"] = "INTELLIGENT_TIERING"

    # TODO add flags for visibility?

    s3_client = boto3.client("s3")
    for path in [NODES_PATH, EDGES_PATH, UNSTANDARDIZED_EDGES_PATH, UNSTANDARDIZED_NODES_PATH]:
        s3_client.upload_file(
            Filename=path.as_posix(),
            Bucket=bucket,
            Key=key + path.name,
            Config=config,
        )


if __name__ == "__main__":
    main()
