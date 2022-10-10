import json
from pathlib import Path
from typing import List, Mapping

from pydantic import BaseModel, Field

from mira.dkg.models import EntityType, Synonym, Xref

HERE = Path(__file__).parent.resolve()
ONTOLOGY_PATH = HERE.joinpath("askemo.json")

#: Keys are values in ASKEMO and values are OBO specificities
EQUIVALENCE_TYPES = {
    "skos:exactMatch": "EXACT",
    "skos:relatedMatch": "RELATED",
    "skos:narrowMatch": "NARROW",
    "skos:broadBarch": "BROAD",
    "oboinowl:hasDbXref": "RELATED",
    "owl:equivalentTo": "EXACT",
}


class Term(BaseModel):
    # TODO combine with dkg.client.Entity class

    id: str
    name: str
    type: EntityType
    obsolete: bool = Field(default=False)
    description: str
    physical_min: float
    physical_max: float
    suggested_data_type: str
    suggested_unit: str
    typical_min: float
    typical_max: float
    xrefs: List[Xref] = Field(default_factory=list)
    synonyms: List[Synonym] = Field(default_factory=list)

    @property
    def prefix(self) -> str:
        """Get the prefix for the term."""
        return self.id.split(":", 1)[0]


def get_askemo_terms() -> Mapping[str, Term]:
    """Load the ontology JSON."""
    rv = {}
    for obj in json.loads(ONTOLOGY_PATH.read_text()):
        term = Term.parse_obj(obj)
        rv[term.id] = term
    return rv


def write(ontology: Mapping[str, Term]) -> None:
    terms = [
        term.dict(exclude_unset=True)
        for _curie, term in sorted(ontology.items())
    ]
    ONTOLOGY_PATH.write_text(
        json.dumps(terms, sort_keys=True, ensure_ascii=False, indent=2)
    )


def lint():
    write(get_askemo_terms())


if __name__ == "__main__":
    lint()
