"""Generate the ASKEM Climate Ontology artifact."""

from typing import Dict

import pandas as pd

from mira.dkg.askemo.api import Term, write, CLIMATE_ONTOLOGY_PATH
from mira.dkg.models import Synonym

__all__ = [
    "get_terms",
]

#: URL to the ASKEM Climate Ontology curation sheet on Google Sheets
URL = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vRIkvJYG50aY3jYbeK0fneObcMTMtPLCxFNCDC_1"
    "8aPB8qr2_qy2yvVSWsr3Uf_BLTVQbd0EgRFEN12/pub?gid=0&single=true&output=tsv"
)


def get_terms() -> Dict[str, Term]:
    """Get ASKEM Climate ontology terms."""
    # df = pd.read_csv(URL, sep="\t")
    df = pd.read_csv("ASKEM Climate Ontology - Sheet1.tsv", sep="\t")
    df = df[df["curie"].notna()]
    df.columns = [c.lower() for c in df.columns]
    terms = (get_term(row) for _, row in df.iterrows())
    return {term.id: term for term in terms}


def get_term(row) -> Term:
    """Get an ASKEM Climate ontology term from a row in a dataframe."""
    synonyms = []
    if pd.notna(abbreviation := row.get("abbreviation")):
        synonyms.append(Synonym(value=abbreviation, type="skos:exactMatch"))

    kwargs = {}
    if synonyms:
        kwargs["synonyms"] = synonyms

    if pd.notna(units := row.get("units")):
        kwargs["dimensionality"] = units

    return Term(
        type="class",
        id=row["curie"],
        name=row["name"],
        description=row["description"] if pd.notna(row["description"]) else "",
        **kwargs,
    )


if __name__ == "__main__":
    write(get_terms(), CLIMATE_ONTOLOGY_PATH)
