"""
Pages in the ESA Data Ontology appear to be fully wrpping the Unified Astronomy Thesaurus

E.g., https://data.esa.int/esado/en/page/?uri=http://astrothesaurus.org/uat/5
has a link a the bottom to download JSON-LD that seems to forward to UAT's API
https://data.esa.int/rest/v1/esado/data?uri=http%3A%2F%2Fastrothesaurus.org%2Fuat%2F5&format=application/ld%2Bjson
"""

import os
import requests
from pyobo import Term, Reference, Obo
from typing import Optional
from pathlib import Path

HERE = Path(__file__).parent.resolve()

url = "https://github.com/astrothesaurus/UAT/raw/master/UAT.json"


def make_term(d, *, parent: Optional[Term] = None, terms):
    identifier = d["uri"].removeprefix("http://astrothesaurus.org/uat/")
    if identifier in terms:
        term = terms[identifier]
    else:
        terms[identifier] = term = Term.from_triple(
            prefix="uat",
            identifier=identifier,
            name=d.get("name"),
            definition=d.get("definition"),
        )
        for synonym in d.get("altLabels") or []:
            term.append_synonym(synonym)
        for related in d.get("related") or []:
            term.append_see_also(Reference(
                prefix="uat",
                identifier=related["uri"].removeprefix("http://astrothesaurus.org/uat/"),
                name=related.get("name"),
            ))

    if parent is not None:
        term.append_parent(parent)

    # Additional data
    change_notes = d.get("changeNotes")
    examples = d.get("examples")  # examples of instances
    scope_notes = d.get("scopeNotes")
    editorial_notes = d.get("editorialNotes")

    unhandled = set(d) - {
        "name", "definition", "altLabels", "related", "changeNotes",
        "scopeNotes", "editorialNotes", "children", "uri", "examples",
    }
    if unhandled:
        raise ValueError(f"missed keys: {unhandled}")

    for child in d.get("children", []):
        make_term(child, parent=term, terms=terms)


def main():
    data = requests.get(url).json()
    terms = {}
    for c in data["children"]:
        make_term(c, terms=terms)

    def func(ont, term):
        return int(term.curie.removeprefix("uat:"))

    class UAT(Obo):
        name = "Unified Astronomy Thesaurus"
        ontology = "uat"
        static_version = "5.0"
        check_bioregistry_prefix = False
        term_sort_key = func

        def iter_terms(self, force: bool = False):
            return terms.values()

    obo = UAT()
    obo_path = HERE.joinpath("uat.obo")
    obograph_path = HERE.joinpath("uat.json")
    obo.write_obo(obo_path)
    os.system(f"robot convert --input {obo_path.as_posix()} --output {obograph_path.as_posix()}")


if __name__ == '__main__':
    main()
