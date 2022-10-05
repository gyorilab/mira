import json
from pathlib import Path
from typing import List, Mapping

from pydantic import BaseModel, Field
from typing_extensions import Literal

HERE = Path(__file__).parent.resolve()
ONTOLOGY_PATH = HERE.joinpath("askemo.json")


class Xref(BaseModel):
    id: str
    type: str


class Synonym(BaseModel):
    value: str
    type: str


class Term(BaseModel):
    type: Literal["class", "property", "instance"]
    prefix: str
    id: str
    name: str
    description: str
    suggested_data_type: str
    suggested_unit: str
    xrefs: List[Xref] = Field(default_factory=list)
    synonyms: List[Synonym] = Field(default_factory=list)


def load() -> Mapping[str, Term]:
    """Load the ontology JSON."""
    rv = {}
    for obj in json.loads(ONTOLOGY_PATH.read_text()):
        term = Term.parse_obj(obj)
        rv[f"{term.prefix}:{term.id}"] = term
    return rv


def write(ontology: dict[str, Term]) -> None:
    terms = [
        term.dict(exclude_unset=True)
        for _curie, term in sorted(ontology.items())
    ]
    ONTOLOGY_PATH.write_text(
        json.dumps(terms, sort_keys=True, ensure_ascii=False, indent=2)
    )


def lint():
    write(load())


if __name__ == "__main__":
    lint()
