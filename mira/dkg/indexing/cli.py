# -*- coding: utf-8 -*-

"""Run the database indexing"""
import click


@click.command(name="indexing")
@click.option(
    "--exist-ok",
    is_flag=True,
    help="If set, skip already set indices silently, otherwise an exception "
         "is raised if attempting to set an index that already exists.",
)
def main(exist_ok: bool = False):
    """Build indexes on the database."""
    from . import index_nodes_on_id
    from mira.dkg.client import Neo4jClient

    client = Neo4jClient()
    click.secho("Indexing all nodes on the id property.", fg="green")
    index_nodes_on_id(client, exist_ok=exist_ok)
