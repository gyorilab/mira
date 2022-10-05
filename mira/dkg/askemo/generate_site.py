"""A script to generate a static site for ASKEMO."""

from pathlib import Path
from typing import List

import bioregistry
import click
import pyobo
from pyobo import Obo
from pyobo.ssg import make_site
from pyobo.struct import make_ad_hoc_ontology

from mira.dkg.askemo.api import Term, load

HERE = Path(__file__).parent.resolve()
ROOT = HERE.parent.parent.parent.resolve()
TERM_DIRECTORY = ROOT.joinpath("docs", "terms")



def _get_term(term: Term) -> pyobo.Term:
    properties = {}
    if term.suggested_data_type:
        properties["suggested_data_type"] = [term.suggested_data_type]
    if term.suggested_unit:
        properties["suggested_unit"] = [term.suggested_unit]

    rv = pyobo.Term(
        reference=pyobo.Reference(
            prefix=term.prefix,
            identifier=term.id,
            name=term.name,
        ),
        definition=term.description,
        synonyms=[
            pyobo.Synonym(
                name=synonym.value,
                specificity=SYNONYM_TYPE_MAP[synonym.type],
            )
            for synonym in term.synonyms or []
        ],
        # FIXME this is lossy at the moment since it looses type
        xrefs=[
            pyobo.Reference.from_curie(xref.id) for xref in term.xrefs or []
        ],
        properties=properties,
    )
    return rv


@click.command()
def main():
    """Generate a static site for ASKEM-O."""
    resource = bioregistry.Resource(
        name="ASKEM Ontology",
        prefix="askemo",
        description="A custom ontology to support the epidemiology use case in ASKEM.",
        pattern="^\\d{7}$",
    )
    obo = make_ad_hoc_ontology(
        resource.prefix,
        resource.name,
        terms=[_get_term(term) for term in load().values()],
    )
    make_site(obo, directory=TERM_DIRECTORY, manifest=True, resource=resource)


if __name__ == "__main__":
    main()
