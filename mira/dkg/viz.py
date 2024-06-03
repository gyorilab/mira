import networkx as nx
from neo4j.graph import Relationship
from mira.dkg.client import Entity


def draw_relations(records, fname, is_full=True):
    """Draw a graph of some DKG records queried from the /relations endpoint."""

    graph = nx.DiGraph()
    graph.graph["rankdir"] = "LR"

    for relation in records:
        if is_full:
            subject = Entity.from_data(relation[0])
            subject_curie = subject.id
            subject_name = subject.name
            p = relation[1]
            predicate_dict = dict(p) if isinstance(p, Relationship) else [dict(r) for r in p]
            predicate_name = p.type
            predicate_curie = predicate_dict["pred"]
            object = Entity.from_data(relation[2])
            object_curie = object.id
            object_name = object.name

            subject_node = f"{subject_name} ({subject_curie})"
            predicate_edge = f"{predicate_name} ({predicate_curie})"
            object_node = f"{object_name} ({object_curie})"

            graph.add_edge(subject_node, object_node, label=predicate_edge,
                           color="red", weight=2)
        else:
            graph.add_edge(relation[0], relation[2], label=relation[1],
                           color="red", weight=2)
    agraph = nx.nx_agraph.to_agraph(graph)
    agraph.draw(path=fname, prog="dot", format="png")
