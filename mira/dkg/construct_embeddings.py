"""Construct low-dimensional embeddings of entities in the MIRA DKG."""

import gzip
import os
import shutil
from tempfile import TemporaryDirectory

import click
from embiggen.embedders import SecondOrderLINEEnsmallen
from ensmallen import Graph

from mira.dkg.construct import upload_s3, UseCasePaths, cases


def _construct_embeddings(upload: bool, use_case_paths: UseCasePaths) -> None:
    with TemporaryDirectory() as directory:
        path = os.path.join(directory, use_case_paths.EDGES_PATH.stem)
        with gzip.open(use_case_paths.EDGES_PATH, "rb") as f_in, open(
            path, "wb"
        ) as f_out:
            shutil.copyfileobj(f_in, f_out)
        graph = Graph.from_csv(
            edge_path=path,
            edge_list_separator="\t",
            sources_column_number=0,
            destinations_column_number=1,
            edge_list_numeric_node_ids=False,
            directed=True,
            name="MIRA-DKG",
        )
    # TODO remove disconnected nodes
    # graph = graph.remove_disconnected_nodes()
    embedding = SecondOrderLINEEnsmallen(embedding_size=32).fit_transform(graph)
    df = embedding.get_all_node_embedding()[0].sort_index()
    df.index.name = "node"
    df.to_csv(use_case_paths.EMBEDDINGS_PATH, sep="\t")
    if upload:
        upload_s3(
            use_case_paths.EMBEDDINGS_PATH, use_case=use_case_paths.use_case
        )


@click.command()
@click.option("--upload", is_flag=True)
@click.option("--use-case", type=click.Choice(sorted(cases)))
def main(upload: bool, use_case: str):
    _construct_embeddings(upload=upload, use_case_paths=UseCasePaths(use_case))


if __name__ == "__main__":
    main()
