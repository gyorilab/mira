"""Construct low-dimensional embeddings of entities in the MIRA DKG."""

import gzip
import os
import shutil
from tempfile import TemporaryDirectory

import click
from embiggen.embedders import SecondOrderLINEEnsmallen
from ensmallen import Graph

from mira.dkg.construct import EDGES_PATH, EMBEDDINGS_PATH, upload_s3


def _construct_embeddings(upload: bool) -> None:
    with TemporaryDirectory() as directory:
        path = os.path.join(directory, EDGES_PATH.stem)
        with gzip.open(EDGES_PATH, "rb") as f_in, open(path, "wb") as f_out:
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
    embedding = SecondOrderLINEEnsmallen(embedding_size=32).fit_transform(graph)
    df = embedding.get_all_node_embedding()[0].sort_index()
    df.index.name = "node"
    df.to_csv(EMBEDDINGS_PATH, sep="\t")
    if upload:
        upload_s3(EMBEDDINGS_PATH)


@click.command()
@click.option("--upload", is_flag=True)
def main(upload: bool):
    _construct_embeddings(upload=upload)


if __name__ == "__main__":
    main()
