"""Generate the ASKEM Climate Ontology artifact."""

from typing import Dict

import pandas as pd

from mira.dkg.askemo.api import Term, write, CLIMATE_ONTOLOGY_PATH
from mira.dkg.models import Synonym

__all__ = [
    "get_askem_climate_terms",
]

#: URL to the ASKEM Climate Ontology curation sheet on Google Sheets
URL = (
    "https://docs.google.com/spreadsheets/d/e/2PACX-1vRIkvJYG50aY3jYbeK0fneObcMTMtPLCxFNCDC_1"
    "8aPB8qr2_qy2yvVSWsr3Uf_BLTVQbd0EgRFEN12/pub?gid=0&single=true&output=tsv"
)


def get_askem_climate_terms() -> Dict[str, Term]:
    """Get ASKEM Climate ontology terms."""
    # df = pd.read_csv(URL, sep="\t")
    df = pd.read_csv("ASKEM Climate Ontology - Sheet1.tsv", sep="\t")
    df = df[df["curie"].notna()]
    df.columns = [c.lower() for c in df.columns]
    terms = [get_term(row) for _, row in df.iterrows()]
    id_to_term: dict[str, Term] = {term.id: term for term in terms}
    name_to_term: dict[str, Term] = {term.name.lower(): term for term in terms}

    for curie, parent in df[["curie", "grouping"]].values:
        if pd.isna(parent):
            continue
        for t in parent.strip().split(","):
            t = t.strip()
            if term := name_to_term.get(t.lower()):
                id_to_term[curie].parents.append(term.id)
            elif term := id_to_term.get(t):
                id_to_term[curie].parents.append(term.id)

    for curie, part_of in df[["curie", "part of"]].values:
        if pd.isna(part_of):
            continue
        for t in part_of.strip().split(","):
            t = t.strip()
            if term := name_to_term.get(t.lower()):
                id_to_term[curie].part_ofs.append(term.id)
            elif term := id_to_term.get(t):
                id_to_term[curie].part_ofs.append(term.id)

    return id_to_term


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
    write(get_askem_climate_terms(), CLIMATE_ONTOLOGY_PATH)
