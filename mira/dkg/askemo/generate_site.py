"""A script to generate a static site for ASKEMO."""

from pathlib import Path

import click
import pyobo
from pyobo.ssg import make_site
from pyobo.struct import make_ad_hoc_ontology

from mira.dkg import ASKEMO
from mira.dkg.askemo.api import Term, get_askemo_terms, EQUIVALENCE_TYPES

HERE = Path(__file__).parent.resolve()
ROOT = HERE.parent.parent.parent.resolve()
ONTOLOGY_DIRECTORY = ROOT.joinpath("docs", "ontology")


def _get_term(term: Term) -> pyobo.Term:
    properties = {}
    if term.suggested_data_type:
        properties["suggested_data_type"] = [term.suggested_data_type]
    if term.suggested_unit:
        properties["suggested_unit"] = [term.suggested_unit]
    if term.physical_min:
        properties["physical_min"] = [term.physical_min]
    if term.physical_max:
        properties["physical_max"] = [term.physical_max]
    if term.typical_min:
        properties["typical_min"] = [term.typical_min]
    if term.typical_max:
        properties["typical_max"] = [term.typical_max]

    rv = pyobo.Term(
        reference=pyobo.Reference.from_curie(term.id, name=term.name),
        definition=term.description,
        synonyms=[
            pyobo.Synonym(
                name=synonym.value,
                specificity=EQUIVALENCE_TYPES[synonym.type],
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
    obo = make_ad_hoc_ontology(
        ASKEMO.prefix,
        ASKEMO.name,
        terms=[_get_term(term) for term in get_askemo_terms().values()],
    )
    make_site(
        obo,
        directory=ONTOLOGY_DIRECTORY,
        manifest=True,
        resource=ASKEMO,
        metaregistry_name="MIRA Epi Metaregistry",
        metaregistry_metaprefix="askemr",
        metaregistry_base_url="http://34.230.33.149:8772/",
    )


if __name__ == "__main__":
    main()
