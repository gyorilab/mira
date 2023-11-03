"""Generate the ASKEM Climate Ontology artifact."""

from collections import defaultdict
from typing import Dict

import pandas as pd

from mira.dkg.askemo.api import CLIMATE_ONTOLOGY_PATH, Term, write
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
    df = pd.read_excel("/Users/cthoyt/Downloads/ASKEM Climate Ontology.xlsx")
    df = df[df["curie"].notna()]
    df.columns = [c.lower() for c in df.columns]

    name_to_id = {
        name.lower(): curie for curie, name in df[["curie", "name"]].values
    }

    parents = defaultdict(list)
    for curie, parent in df[["curie", "parent"]].values:
        if pd.isna(parent):
            continue
        for t in parent.strip().split(","):
            t = t.strip()
            if t == "root":
                continue
            term_id = name_to_id[t.lower()]
            parents[curie].append(term_id)
    parents = dict(parents)

    part_ofs = defaultdict(list)
    for curie, part_of in df[["curie", "part of"]].values:
        if pd.isna(part_of):
            continue
        for t in part_of.strip().split(","):
            t = t.strip().lower()
            term_id = name_to_id[t]
            part_ofs[curie].append(term_id)
    part_ofs = dict(part_ofs)

    terms = [get_term(row, parents=parents, part_ofs=part_ofs) for _, row in df.iterrows()]
    id_to_term: dict[str, Term] = {term.id: term for term in terms}

    return id_to_term


def get_term(row, parents, part_ofs) -> Term:
    """Get an ASKEM Climate ontology term from a row in a dataframe."""
    curie = row["curie"]

    synonyms = []
    if pd.notna(abbreviation := row.get("abbreviation")):
        synonyms.append(Synonym(value=abbreviation, type="skos:exactMatch"))
    if pd.notna(symbol := row.get("symbol")):
        synonyms.append(Synonym(value=symbol, type="referenced_by_symbol"))

    kwargs = {}
    if synonyms:
        kwargs["synonyms"] = synonyms
    if pd.notna(units := row.get("units")):
        if units != "🤷":
            # the shrug emoji represents a variadic unit type, which is itself a parameter
            kwargs["dimensionality"] = units

    if curie in parents:
        kwargs["parents"] = parents[curie]
    if curie in part_ofs:
        kwargs["part_ofs"] = part_ofs[curie]

    return Term(
        type="class",
        id=curie,
        name=row["name"].strip(),
        description=row["description"].replace("\n", " ")
        if pd.notna(row["description"])
        else "",
        **kwargs,
    )


if __name__ == "__main__":
    write(get_askem_climate_terms(), CLIMATE_ONTOLOGY_PATH)
