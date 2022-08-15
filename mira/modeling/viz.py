"""Visualization of transition models."""

from pathlib import Path
from typing import Union

import pygraphviz as pgv
from typing_extensions import Self

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
        for i, (_k, transition) in enumerate(sorted(model.transitions.items())):
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

    def write(self, path: Union[str, Path], prog: str = "dot", args: str = "") -> None:
        """Write the graphical representation to a file.

        :param path: The path to the output file
        :param prog: The graphviz layout program to use, such as "dot", "neato", etc.
        :param args: Additional arguments to pass to the graphviz bash program
        """
        path = Path(path).expanduser().resolve()
        self.graph.draw(path, prog=prog, args=args)


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
