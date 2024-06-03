import networkx as nx


def draw_relations(records, fname, is_full=False):
    """Draw a graph of some DKG records queried from the /relations endpoint."""

    graph = nx.DiGraph()
    graph.graph["rankdir"] = "LR"

    for relation in records:
        if is_full:
            subject_curie = relation['subject']['id']
            subject_name = relation['subject']['name']
            object_curie = relation['object']['id']
            object_name = relation['object']['name']
            predicate_name = relation['predicate'].get('type')
            predicate_curie = relation['predicate']['pred']

            subject_node = f"{subject_name} ({subject_curie})"
            predicate_edge = f"{predicate_name} ({predicate_curie})" \
                if predicate_name else predicate_curie
            object_node = f"{object_name} ({object_curie})"

            graph.add_edge(subject_node, object_node, label=predicate_edge,
                           color="red", weight=2)
        else:
            graph.add_edge(relation['subject'], relation['object'],
                           label=relation['predicate'],
                           color="red", weight=2)
    agraph = nx.nx_agraph.to_agraph(graph)
    agraph.draw(path=fname, prog="dot", format="png")
