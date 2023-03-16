import time

from tqdm import tqdm

from mira.dkg.client import Neo4jClient


def index_nodes_on_id(client: Neo4jClient, exist_ok: bool = False):
    """Index all nodes on the id property

    Parameters
    ----------
    client :
        Neo4jClient instance to the graph database to be indexed
    exist_ok :
        If False, raise an exception if the index already exists. Default: False.
    """
    # A label has to be provided to build the index, so we have to loop over
    # all labels and build the index for each one.
    labels = [
        ll[0]
        for ll in client.query_tx("CALL db.labels() YIELD label RETURN label")
    ]
    print(f"Indexing nodes on id property for the following labels: {labels}")
    for label in tqdm(labels, desc="Indexing nodes on id", unit="label"):
        client.create_single_property_node_index(
            index_name=f"node_id_{label.lower()}",
            label=label,
            property_name="id",
            exist_ok=exist_ok,
        )
        # Wait a bit just to be on the safe side
        time.sleep(0.1)
