"""A script to generate a static site for ASKEMO."""

from pathlib import Path

import click
import pyobo
from pyobo.ssg import make_site
from pyobo.struct import make_ad_hoc_ontology

from mira.dkg import ASKEMO
from mira.dkg.askemo.api import Term, get_askemo_terms, SYNONYM_TYPES, REFERENCED_BY_LATEX, REFERENCED_BY_SYMBOL

HERE = Path(__file__).parent.resolve()
ROOT = HERE.parent.parent.parent.resolve()
ONTOLOGY_DIRECTORY = ROOT.joinpath("docs", "ontology")

SYMBOL_SYNONYM_TEXT_TYPEDEF = pyobo.SynonymTypeDef(REFERENCED_BY_SYMBOL, "Symbol Text", specificity="RELATED")
SYMBOL_SYNONYM_LATEX_TYPEDEF = pyobo.SynonymTypeDef(REFERENCED_BY_LATEX, "Symbol LaTeX", specificity="RELATED")
SYNONYM_TYPEDEFS = [SYMBOL_SYNONYM_LATEX_TYPEDEF, SYMBOL_SYNONYM_TEXT_TYPEDEF]
SYNONYM_TYPEDEFS_DICT = {
    synonym_typedef.id: synonym_typedef
    for synonym_typedef in SYNONYM_TYPEDEFS
}


def _get_term(term: Term) -> pyobo.Term:
    properties = {}
    if term.suggested_data_type is not None:
        properties["suggested_data_type"] = [term.suggested_data_type]
    if term.suggested_unit is not None:
        properties["suggested_unit"] = [term.suggested_unit]
    if term.physical_min is not None:
        properties["physical_min"] = [term.physical_min]
    if term.physical_max is not None:
        properties["physical_max"] = [term.physical_max]
    if term.typical_min is not None:
        properties["typical_min"] = [term.typical_min]
    if term.typical_max is not None:
        properties["typical_max"] = [term.typical_max]

    rv = pyobo.Term(
        reference=pyobo.Reference.from_curie(term.id, name=term.name),
        definition=term.description,
        synonyms=[
            pyobo.Synonym(
                name=synonym.value,
                specificity=SYNONYM_TYPES[synonym.type],
                type=SYNONYM_TYPEDEFS_DICT.get(synonym.type),
            )
            for synonym in term.synonyms or []
        ],
        # FIXME this is lossy at the moment since it looses type
        xrefs=[
            pyobo.Reference.from_curie(xref.id) for xref in term.xrefs or []
        ],
        properties=properties,
        parents=[
            pyobo.Reference.from_curie(parent_curie)
            for parent_curie in term.parents
        ],
    )
    return rv


@click.command()
def main():
    """Generate a static site for ASKEM-O."""
    obo = make_ad_hoc_ontology(
        ASKEMO.prefix,
        ASKEMO.name,
        terms=[_get_term(term) for term in get_askemo_terms().values()],
        _synonym_typedefs=SYNONYM_TYPEDEFS,
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
