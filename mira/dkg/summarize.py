from typing import Optional

import click
from tabulate import tabulate

from mira.dkg.client import Neo4jClient


@click.command()
@click.option("--url", default="bolt://0.0.0.0:8770")
@click.option("--user")
@click.option("--password")
def main(url: Optional[str], user: Optional[str], password: Optional[str]):
    """Summarize the contents of a neo4j instance."""
    client = Neo4jClient(url=url, user=user, password=password)
    c = client.get_node_counter()
    click.echo(
        tabulate(c.most_common(), headers=["label", "count"], tablefmt="github")
    )


if __name__ == "__main__":
    main()
