from mira.examples.sir import sir, sir_2_city
from mira.metamodel.templates import TemplateModelComparison
from mira.dkg.web_client import is_ontological_child_web


def test_template_model_comp_graph_export():
    tmc = TemplateModelComparison(template_models=[sir, sir_2_city],
                                  refinement_func=is_ontological_child_web)

    # Check that the graph export is correct
    graph_data = tmc.model_comparison

    # One node per template per TemplateModel + one node per concept per
    # template per TemplateModel
    template_node_count = len(sir.templates) + len(sir_2_city.templates)
    concept_node_count = sum(len(t.concepts) for t in sir.templates) + sum(
        len(t.concepts) for t in sir_2_city.templates
    )
    assert graph_data.nodes == template_node_count + concept_node_count
