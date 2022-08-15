import click
from typing import Counter, Optional

from mira.dkg.client import Neo4jClient

from tabulate import tabulate


@click.command()
@click.option("--url")
@click.option("--user")
@click.option("--password")
def main(url: Optional[str], user: Optional[str], password: Optional[str]):
    """Summarize the contents of a neo4j instance."""
    client = Neo4jClient(url=url, user=user, password=password)
    c = client.get_node_counter()
    click.echo(tabulate(c.most_common(), headers=["label", "count"], tablefmt="github"))


if __name__ == '__main__':
    main()
