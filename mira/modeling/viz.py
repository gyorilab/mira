"""Visualization of transition models."""

import itertools as itt
from pathlib import Path
from typing import Optional, Union

import pygraphviz as pgv

from mira.metamodel import TemplateModel
from mira.modeling import Model

__all__ = [
    "GraphicalModel",
]


class GraphicalModel:
    """Create a graphical representation of a transition model."""

    def __init__(self, model: Model):
        self.graph = pgv.AGraph(
            strict=True,
            directed=True,
        )
        for variable in model.variables.values():
            identifiers = variable.data.get('identifiers')
            contexts = variable.data.get('context')
            name = variable.data.get('name', str(variable.key))
            if not identifiers and not contexts:
                label = name
                shape = "oval"
            else:
                cc = " | ".join(f"{{{k} | {v}}}" for k, v in itt.chain(identifiers, contexts))
                label = f"{{{name} | {cc}}}"
                shape = "record"
            self.graph.add_node(
                variable.key,
                label=label,
                shape=shape,
            )
        for i, (_k, transition) in enumerate(model.transitions.items()):
            if transition.consumed and transition.produced:
                color = "blue"
            elif transition.consumed and not transition.produced:
                color = "red"
            elif transition.produced and not transition.consumed:
                color = "orange"
            else:
                color = "black"
            key = f"T{i}"
            self.graph.add_node(
                key,
                shape="square",
                color=color,
                style="filled",
                # fontsize=10,
                fillcolor=color,
                label="",
                fixedsize="true",
                width=0.2,
                height=0.2,
            )
            for consumed in transition.consumed:
                self.graph.add_edge(
                    consumed.key,
                    key,
                )
            for produced in transition.produced:
                self.graph.add_edge(
                    key,
                    produced.key,
                )
            for controller in transition.control:
                self.graph.add_edge(
                    controller.key,
                    key,
                    color="blue",
                )

    @classmethod
    def from_template_model(cls, template_model: TemplateModel) -> "GraphicalModel":
        """Get a graphical model from a template model."""
        return cls(Model(template_model))

    def write(
        self,
        path: Union[str, Path],
        prog: str = "dot",
        args: str = "",
        format: Optional[str] = None,
    ) -> None:
        """Write the graphical representation to a file.

        Parameters
        ----------
        path :
            The path to the output file
        prog :
            The graphviz layout program to use, such as "dot", "neato", etc.
        format :
            Set the file format explicitly
        args :
            Additional arguments to pass to the graphviz bash program
        """
        path = Path(path).expanduser().resolve()
        self.graph.draw(path, format=format, prog=prog, args=args)

    @classmethod
    def for_jupyter(cls, template_model, name="model.png", **kwargs):
        """Display in jupyter."""
        from IPython.display import Image

        GraphicalModel.from_template_model(template_model).write(name)
        return Image('model.png', **kwargs)

def _main():
    from mira.examples.nabi2021 import nabi2021
    from mira.examples.sir import sir, sir_2_city
    from mira.examples.jin2022 import seird_stratified
    from mira.examples.chime import sviivr

    gm = GraphicalModel.from_template_model(sir)
    gm.write("~/Desktop/sir_example.png")

    gm = GraphicalModel.from_template_model(sir_2_city)
    gm.write("~/Desktop/sir_2_city_example.png")

    GraphicalModel.from_template_model(nabi2021).write("~/Desktop/nabi2021.png")

    gm = GraphicalModel.from_template_model(seird_stratified)
    gm.write("~/Desktop/seird_stratified.png")

    gm = GraphicalModel.from_template_model(sviivr)
    gm.write("~/Desktop/sviivr.png")


if __name__ == "__main__":
    _main()
