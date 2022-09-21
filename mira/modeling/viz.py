"""Visualization of transition models."""

from pathlib import Path
from typing import Optional, Union

import pygraphviz as pgv

from mira.modeling import Model, TemplateModel

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
        for variable in model.variables:
            if isinstance(variable, str):
                label = variable
                shape = "oval"
            else:
                name, *contexts = variable
                cc = " | ".join(f"{{{k} | {v}}}" for k, v in contexts)
                label = f"{{{name} | {cc}}}"
                shape = "record"
            self.graph.add_node(
                variable,
                label=label,
                shape=shape,
            )
        for i, (_k, transition) in enumerate(model.transitions.items()):
            key = f"T{i}"
            self.graph.add_node(
                key,
                shape="square",
                color="blue",
                style="filled",
                # fontsize=10,
                fillcolor="blue",
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


def _main():
    from mira.examples.sir import sir, sir_2_city

    model = Model(sir)
    gm = GraphicalModel(model)
    gm.write("~/Desktop/sir_example.png")

    model = Model(sir_2_city)
    gm = GraphicalModel(model)
    gm.write("~/Desktop/sir_2_city_example.png")


if __name__ == "__main__":
    _main()
