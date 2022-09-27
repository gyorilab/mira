import unittest

from mira.dkg.web_client import is_ontological_child
from mira.examples.sir import sir, cities
from mira.metamodel.templates import TemplateModelDelta, TemplateModel


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

        # one node per template per TemplateModel
        self.assertEqual(
            len(tmd.comparison_graph.nodes),
            2 * len(self.sir.templates),
            f"len(nodes)={len(tmd.comparison_graph.edges)}",
        )
        # Two edges (both directions) per Template per TemplateModel
        self.assertEqual(
            len(tmd.comparison_graph.edges),
            2 * len(self.sir.templates),
            f"len(edges)={len(tmd.comparison_graph.edges)}",
        )
        self.assert_(
            all("is_refinement" != d["type"] for _, _, d in tmd.comparison_graph.edges(data=True))
        )
        self.assert_(
            all("is_equal" == d["type"] for _, _, d in tmd.comparison_graph.edges(data=True))
        )

    def test_equal_context(self):
        tmd_context = TemplateModelDelta(
            self.sir_boston, self.sir_boston, refinement_function=is_ontological_child
        )

        # one node per template per TemplateModel
        self.assertEqual(
            len(tmd_context.comparison_graph.nodes),
            2 * len(self.sir.templates),
            f"len(nodes)={len(tmd_context.comparison_graph.edges)}",
        )
        # Two edges (both directions) per Template per TemplateModel
        self.assertEqual(
            len(tmd_context.comparison_graph.edges),
            2 * len(self.sir.templates),
            f"len(edges)={len(tmd_context.comparison_graph.edges)}",
        )
        self.assert_(
            all(
                "is_refinement" != d["type"]
                for _, _, d in tmd_context.comparison_graph.edges(data=True)
            )
        )
        self.assert_(
            all(
                "is_equal" == d["type"] for _, _, d in tmd_context.comparison_graph.edges(data=True)
            )
        )

    def test_not_equal_or_refinement(self):
        tm_delta_nothing = TemplateModelDelta(
            self.sir_boston, self.sir_nyc, refinement_function=is_ontological_child
        )

        # one node per template per TemplateModel
        self.assertEqual(
            len(tm_delta_nothing.comparison_graph.nodes),
            2 * len(self.sir.templates),
            f"len(nodes)={len(tm_delta_nothing.comparison_graph.edges)}",
        )

        # No edges should be present
        self.assertEqual(
            len(tm_delta_nothing.comparison_graph.edges),
            0,
            f"len(edges)={len(tm_delta_nothing.comparison_graph.edges)}",
        )

    def test_refinement(self):
        tmd_vs_boston = TemplateModelDelta(self.sir, self.sir_boston, is_ontological_child)
        tmd_vs_nyc = TemplateModelDelta(self.sir, self.sir_nyc, is_ontological_child)

        self.assert_(
            all(
                "is_refinement" == d["type"]
                for _, _, d in tmd_vs_boston.comparison_graph.edges(data=True)
            )
        )
        self.assert_(
            all(
                "is_equal" != d["type"]
                for _, _, d in tmd_vs_boston.comparison_graph.edges(data=True)
            )
        )
        self.assert_(
            all(
                "is_refinement" == d["type"]
                for _, _, d in tmd_vs_nyc.comparison_graph.edges(data=True)
            )
        )
        self.assert_(
            all(
                "is_equal" != d["type"]
                for _, _, d in tmd_vs_nyc.comparison_graph.edges(data=True)
            )
        )
