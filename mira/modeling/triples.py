"""Generate knowledge-graph-ready triples from template models."""

import csv
import itertools as itt
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional, Tuple, Union

from mira.pydantic_setup import BaseModel

from mira.dkg.constants import EDGE_HEADER
from mira.metamodel import Template, TemplateModel
from mira.metamodel.templates import Config

if TYPE_CHECKING:
    import pandas

__all__ = [
    "TriplesGenerator",
]

CO_OCCURS = "askemo:0000017"

RELATIONS = {
    CO_OCCURS: "co-occurs with",
}


class Triple(BaseModel):
    """Represents a triple of 3 CURIEs."""

    sub: str
    pred: str
    obj: str

    def as_tuple(self) -> Tuple[str, str, str]:
        return self.sub, self.pred, self.obj


class TriplesGenerator:
    """Generates triples from a templated model to include in the DKG."""

    def __init__(
        self,
        model: TemplateModel,
        config: Optional[Config] = None,
        skip_prefixes: Optional[Iterable[str]] = None,
    ):
        """
        Parameters
        ----------
        model:
            A template model
        config:
            Configuration for creating canonical CURIEs
        skip_prefixes:
            A list, set, or iterable of strings representing
            prefixes that should be skipped.
        """
        self.model = model
        self.triples = {}
        self.skip_prefixes = {""}
        if skip_prefixes:
            self.skip_prefixes.update(skip_prefixes)
        for template in model.templates:
            for triple in self.iter_triples(template, config=config):
                if triple.sub == triple.obj:
                    continue
                self.triples[triple.as_tuple()] = triple

    def to_dataframe(self) -> "pandas.DataFrame":
        """Get all triples as a pandas dataframe."""
        import pandas

        columns = ["subject", "predicate", "object"]
        df = pandas.DataFrame(
            [t.as_tuple() for t in self.triples.values()],
            columns=columns,
        )
        df = df.drop_duplicates()
        df = df[df["subject"] != df["object"]]
        df = df.sort_values(columns)
        return df

    def write_neo4j_bulk(self, path: Union[str, Path]) -> None:
        """Write a file that can be bulk imported in neo4j."""
        with open(path, "w") as file:
            writer = csv.writer(file, delimiter="\t")
            writer.writerow(EDGE_HEADER)
            writer.writerows(
                (
                    triple.sub,
                    triple.obj,
                    RELATIONS[triple.pred],
                    triple.pred,
                    "template",  # TODO add extra metadata to models?
                    "template",
                    "",
                )
                for _, triple in sorted(self.triples.items())
            )

    def iter_triples(
        self, template: Template, config: Optional[Config] = None
    ) -> Iterable[Triple]:
        """Iterate triples from a template."""
        for a, b in itt.product(template.get_concepts(), repeat=2):
            sub_prefix, sub_id = a.get_curie(config=config)
            obj_prefix, obj_id = b.get_curie(config=config)
            if (
                sub_prefix in self.skip_prefixes
                or obj_prefix in self.skip_prefixes
            ):
                continue
            yield Triple(
                sub=f"{sub_prefix}:{sub_id}",
                pred=CO_OCCURS,
                obj=f"{obj_prefix}:{obj_id}",
            )
