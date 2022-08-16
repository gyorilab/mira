"""
Neo4j Setup:

1. Find conf file, somewhere like ``/usr/local/Cellar/neo4j/4.1.3/libexec/conf/neo4j.conf`` for brew installation
2. comment out this line: ``dbms.directories.import=import`` c.f.
   https://stackoverflow.com/questions/36922843/neo4j-3-x-load-csv-absolute-file-path
3. Data are stored in ``/usr/local/var/neo4j/data/databases``
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
from click_default_group import DefaultGroup
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
EDGES_PATHS: dict[str, Path] = {prefix: DEMO_MODULE.join(name=f"edges_{prefix}.tsv") for prefix in PREFIXES}
EDGE_HEADER = (":START_ID", ":END_ID", ":TYPE", "pred:string", "source:string", "graph:string")

@click.group(cls=DefaultGroup, default="build", default_if_no_args=True)
def main():
    pass


@main.command()
@click.pass_context
def build(ctx: click.Context):
    ctx.invoke(graphs)
    ctx.invoke(load)


LABELS = {"http://www.w3.org/2000/01/rdf-schema#isDefinedBy": "is defined by"}


@main.command()
def graphs():
    if EDGE_NAMES_PATH.is_file():
        edge_names = json.loads(EDGE_NAMES_PATH.read_text())
    else:
        edge_names = {}
        for edge_prefix in ["oboinowl", "ro", "bfo"]:
            click.secho(f"Caching {bioregistry.get_name(edge_prefix)}", fg="green", bold=True)
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
        click.secho(f"{bioregistry.get_name(prefix)} ({len(_graphs)} graphs)", fg="green", bold=True)

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
                    )

            counter = Counter(node.prefix for node in graph.nodes if node.type != "PROPERTY")
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

            http_nodes.extend(node.id for node in graph.nodes if node.id.startswith("http"))

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
                for edge in tqdm(sorted(graph.edges, key=methodcaller("as_tuple")), unit="edge", unit_scale=True)
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
        writer.writerow(("id:ID", ":LABEL", "name:string", "synonyms:string[]", "obsolete:boolean", "type:string"))
        writer.writerows((node for _curie, node in tqdm(sorted(nodes.items()), unit="node", unit_scale=True)))
    print("output edges to", NODES_PATH)

    # CAT edge files together
    with EDGES_PATH.open("w") as file:
        writer = csv.writer(file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(EDGE_HEADER)
        for prefix, edge_path in tqdm(sorted(EDGES_PATHS.items()), desc="cat edges"):
            with edge_path.open() as edge_file:
                reader = csv.reader(edge_file, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
                _header = next(reader)
                writer.writerows(reader)

    http_counter = Counter(http_nodes)
    with HTTP_FAILURES_PATH.open("w") as file:
        for url, count in http_counter.most_common():
            print(url, count, sep="\t", file=file)


@main.command()
@click.option("--restart", is_flag=True)
def load(restart: bool):
    command = dedent(
        f"""\
            neo4j-admin import \\
              --database mira \\
              --force \\
              --delimiter='\\t' \\
              --skip-duplicate-nodes=true \\
              --skip-bad-relationships=true \\
              --nodes {NODES_PATH.as_posix()}
        """
    ).rstrip()

    for _, edges_path in sorted(EDGES_PATHS.items()):
        command += f" \\\n  --relationships {edges_path.as_posix()}"

    click.secho("Running shell command:")
    click.secho(command, fg="blue")
    os.system(command)  # noqa:S605

    if restart:
        time.sleep(10)
        click.secho("restarting neo4j...")
        os.system("brew services restart neo4j")


if __name__ == "__main__":
    main()
