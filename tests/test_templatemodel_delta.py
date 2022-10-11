import unittest
from itertools import product, permutations
from typing import Tuple

from mira.dkg.web_client import is_ontological_child
from mira.examples.sir import sir, cities
from mira.metamodel.templates import TemplateModelDelta, TemplateModel, get_concept_graph_key


concept_edge_labels = ["subject", "controller", "outcome"]


def get_counts(tmd: TemplateModelDelta) -> Tuple[int, int]:
    # Node count:
    # one node per template per TemplateModel + one node per concept,
    # unless they're merged
    both_templates = tmd.template_model1.templates + tmd.template_model2.templates
    concept_nodes = set()
    for t in both_templates:
        concept_nodes |= {get_concept_graph_key(c) for c in t.get_concepts()}
    node_count = len(both_templates) + len(concept_nodes)

    # one edge per concept per template model + two edges per template
    # equality + one edge per template refinements + one edge per
    # concept refinement
    template_concept_edges = sum(len(t.get_concepts()) for t in both_templates)
    template_equal_edges = 2 * sum(
        t1.is_equal_to(t2, with_context=True)
        for t1, t2 in product(tmd.template_model1.templates, tmd.template_model2.templates)
    )
    template_refinement_edges = sum(
        (not t1.is_equal_to(t2)) and
        t1.refinement_of(t2, refinement_func=tmd.refinement_func, with_context=True)
        for t1, t2 in product(tmd.template_model1.templates, tmd.template_model2.templates)
    )
    concept_refinement_edges = 0
    for templ1 in tmd.template_model1.templates:
        for conc1 in templ1.get_concepts():
            for templ2 in tmd.template_model2.templates:
                for conc2 in templ2.get_concepts():
                    if conc1.is_equal_to(conc2, with_context=True):
                        continue
                    if conc1.refinement_of(conc2,
                                           refinement_func=tmd.refinement_func,
                                           with_context=True):
                        concept_refinement_edges += 1
                    if conc2.refinement_of(conc1,
                                           refinement_func=tmd.refinement_func,
                                           with_context=True):
                        concept_refinement_edges += 1
    edge_count = (
        template_concept_edges
        + template_equal_edges
        + template_refinement_edges
        + concept_refinement_edges
    )

    return node_count, edge_count


class TestTemplateModelDelta(unittest.TestCase):
    def setUp(self) -> None:
        nyc, boston = cities
        self.sir = sir
        self.sir_boston = TemplateModel(
            templates=[t.with_context(city=boston) for t in sir.templates]
        )
        self.sir_nyc = TemplateModel(templates=[t.with_context(city=nyc) for t in sir.templates])

    def test_equal_no_context(self):
        tmd = TemplateModelDelta(self.sir, self.sir, refinement_function=is_ontological_child)

        # one node per template per TemplateModel + one node per concept,
        # unless they're merged
        node_count, edge_count = get_counts(tmd)
        self.assertEqual(
            len(tmd.comparison_graph.nodes),
            node_count,
            f"len(nodes)={len(tmd.comparison_graph.nodes)}",
        )

        self.assertEqual(
            len(tmd.comparison_graph.edges),
            edge_count,
            f"len(edges)={len(tmd.comparison_graph.edges)}",
        )
        self.assert_(
            all("is_refinement" != d["label"] for _, _, d in tmd.comparison_graph.edges(data=True))
        )
        self.assert_(
            all(
                d["label"] in ["is_equal"] + concept_edge_labels
                for _, _, d in tmd.comparison_graph.edges(data=True)
            )
        )

    def test_equal_context(self):
        tmd_context = TemplateModelDelta(
            self.sir_boston, self.sir_boston, refinement_function=is_ontological_child
        )
        node_count, edge_count = get_counts(tmd_context)
        # one node per template per TemplateModel
        self.assertEqual(
            len(tmd_context.comparison_graph.nodes),
            node_count,
            f"len(nodes)={len(tmd_context.comparison_graph.edges)}",
        )
        # Two edges (both directions) per Template per TemplateModel
        self.assertEqual(
            len(tmd_context.comparison_graph.edges),
            edge_count,
            f"len(edges)={len(tmd_context.comparison_graph.edges)}",
        )
        self.assert_(
            all(
                "is_refinement" != d["label"]
                for _, _, d in tmd_context.comparison_graph.edges(data=True)
            )
        )
        self.assert_(
            all(
                d["label"] in ["is_equal"] + concept_edge_labels for _, _,
                                                  d in tmd_context.comparison_graph.edges(data=True)
            )
        )

    def test_not_equal_or_refinement(self):
        tm_delta_nothing = TemplateModelDelta(
            self.sir_boston, self.sir_nyc, refinement_function=is_ontological_child
        )
        # one node per template per TemplateModel + one node per concept
        node_count, edge_count = get_counts(tm_delta_nothing)
        self.assertEqual(
            len(tm_delta_nothing.comparison_graph.nodes),
            # 2 * len(self.sir.templates + ),
            node_count,
            f"len(nodes)={len(tm_delta_nothing.comparison_graph.edges)}",
        )

        # Only edges between Templates and Concepts should be present
        self.assertEqual(
            len(tm_delta_nothing.comparison_graph.edges),
            edge_count,
            f"len(edges)={len(tm_delta_nothing.comparison_graph.edges)}",
        )

    def test_refinement(self):
        tmd_vs_boston = TemplateModelDelta(self.sir, self.sir_boston, is_ontological_child)
        tmd_vs_nyc = TemplateModelDelta(self.sir, self.sir_nyc, is_ontological_child)

        self.assert_(
            all(
                d["label"] in ["refinement_of"] + concept_edge_labels
                for _, _, d in tmd_vs_boston.comparison_graph.edges(data=True)
            )
        )
        self.assert_(
            all(
                "is_equal" != d["label"]
                for _, _, d in tmd_vs_boston.comparison_graph.edges(data=True)
            )
        )
        self.assert_(
            all(
                d["label"] in ["refinement_of"] + concept_edge_labels
                for _, _, d in tmd_vs_nyc.comparison_graph.edges(data=True)
            )
        )
        self.assert_(
            all("is_equal" != d["label"] for _, _, d in tmd_vs_nyc.comparison_graph.edges(data=True))
        )
