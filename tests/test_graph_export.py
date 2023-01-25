from itertools import product, chain

from mira.examples.sir import sir
from mira.metamodel.templates import TemplateModelComparison, TemplateModel
from mira.dkg.web_client import is_ontological_child_web


def test_template_model_comp_graph_export():
    # Check counts
    # Check identifications
    # check expected edges
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
    assert isinstance(list(graph_data.nodes.values())[0].model_id, int)
    assert list(graph_data.nodes.values())[0].model_id >= 0
    assert all(isinstance(k, int) for k in graph_data.template_models.keys())
    assert all(k >= 0 for k in graph_data.template_models.keys())
    model_id_refs = {k for k in graph_data.template_models.keys()}
    model_id_refs_nodes = {n.model_id for n in graph_data.nodes.values()}
    assert model_id_refs == model_id_refs_nodes

    # One node per template per TemplateModel + one node per concept per
    # template per TemplateModel
    template_node_count = len(sir.templates) + len(sir_2_city.templates)
    concept_node_count = sum(len(t.concepts) for t in sir.templates) + sum(
        len(t.concepts) for t in sir_2_city.templates
    )
    assert graph_data.nodes == template_node_count + concept_node_count
