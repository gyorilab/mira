from itertools import product, chain

from mira.examples.sir import sir
from mira.metamodel.templates import TemplateModelComparison, TemplateModel, \
    Template, Concept
from mira.dkg.web_client import is_ontological_child_web


def test_template_model_comp_graph_export():
    # Check counts
    # Check identifications
    # check expected edges

    # This will create a copy SIR model with context -> should have a
    # refinement edge between each corresponding pair of nodes in the graph
    sir_w_context = TemplateModel(
        templates=[
            t.with_context(location="geonames:4930956") for t in sir.templates
        ],
        parameters=sir.parameters,
        initials=sir.initials,
    )
    tmc = TemplateModelComparison(
        template_models=[sir, sir_w_context],
        refinement_func=is_ontological_child_web,
    )

    # Check that the graph export is correct
    graph_data = tmc.model_comparison

    # Check that model ids are integers and non-negative
    assert len(graph_data.nodes.values()) > 0
    # {model_id: {node_id: Concept|Template}}
    assert isinstance(list(graph_data.nodes.values())[0], dict)
    assert isinstance(list(list(graph_data.nodes.values())[0].values())[0],
                      (Concept, Template))
    assert list(list(graph_data.nodes.values())[0].keys())[0] >= 0
    assert all(isinstance(k, int) for k in graph_data.template_models.keys())
    assert all(k >= 0 for k in graph_data.template_models.keys())
    model_id_refs = {k for k in graph_data.template_models.keys()}

    model_id_refs_nodes = {model_id for model_id in graph_data.nodes.keys()}
    assert model_id_refs == model_id_refs_nodes

    # One node per template per TemplateModel + one node per concept per
    # template per TemplateModel
    template_node_count = len(sir.templates) + len(sir_w_context.templates)
    assert template_node_count == 4

    concept_keys = set()
    for t in chain(sir.templates, sir_w_context.templates):
        for c in t.get_concepts():
            concept_keys.add(c.get_key())

    concept_node_count = len(concept_keys)
    assert concept_node_count == 6
    assert 10 == template_node_count + concept_node_count

    # Check that all models are represented in the node lookup
    assert len(graph_data.nodes) == len(graph_data.template_models)

    # Check that the total count of nodes is as expected
    total_count = 0
    for nodes in graph_data.nodes.values():
        total_count += len(nodes)
    assert total_count == template_node_count + concept_node_count

    # One intra edge per concept per template per TemplateModel
    assert len(graph_data.intra_model_edges) == concept_node_count + template_node_count

    # (One inter edge per refinement + one inter edge per equality) per TemplateModel
    concept_equal_edges = 0
    template_equal_edges = 0
    concept_refinement_edges = 0
    template_refinement_edges = 0
    seen_concept_pairs = set()
    for t1, t2 in product(sir.templates, sir_w_context.templates):
        if t1.is_equal_to(t2, with_context=True):
            template_equal_edges += 1
        if t1.refinement_of(
            t2, refinement_func=is_ontological_child_web, with_context=True
        ):
            template_refinement_edges += 1
        if t2.refinement_of(
            t1, refinement_func=is_ontological_child_web, with_context=True
        ):
            template_refinement_edges += 1
        for c1, c2 in product(t1.get_concepts(), t2.get_concepts()):
            if (c1.get_key(), c2.get_key()) in seen_concept_pairs:
                continue
            if c1.is_equal_to(c2, with_context=True):
                concept_equal_edges += 1
            if c1.refinement_of(
                c2, refinement_func=is_ontological_child_web, with_context=True
            ):
                concept_refinement_edges += 1
            if c2.refinement_of(
                c1, refinement_func=is_ontological_child_web, with_context=True
            ):
                concept_refinement_edges += 1
            seen_concept_pairs.add((c1.get_key(), c2.get_key()))

    # Check that the counts are as expected
    assert template_equal_edges == 0
    assert template_refinement_edges == 2
    assert concept_equal_edges == 0
    assert concept_refinement_edges == 3

    # check that the total number of inter edges is as expected and
    # corresponds to what's in the graph data
    inter_edge_count = (
        template_equal_edges
        + template_refinement_edges
        + concept_refinement_edges
        + concept_equal_edges
    )
    assert inter_edge_count == 5
    assert len(graph_data.inter_model_edges) == inter_edge_count
