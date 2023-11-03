"""Get physical constants from wikidata."""

from typing import List, Mapping, Any
import logging
import requests
from .resources import get_resource_path

__all__ = [
    "get_physical_constant_terms",
]

logger = logging.getLogger(__name__)

#: Wikidata SPARQL endpoint. See https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service#Interfacing
WIKIDATA_ENDPOINT = "https://query.wikidata.org/bigdata/namespace/wdq/sparql"

SPARQL = """\
SELECT 
  ?item ?itemLabel ?itemDescription ?itemAltLabel ?value ?defining_formula 
  (group_concat(?nist;separator="|") as ?nists)
  (group_concat(?goldbook; separator="|") as ?goldbooks)
  (group_concat(?latex; separator="||") as ?latexes)
WHERE 
{
  ?item wdt:P31 wd:Q173227 .
  OPTIONAL { ?item wdt:P1181 ?value . }
  OPTIONAL { ?item wdt:P2534 ?defining_formula . }
  OPTIONAL { ?item wdt:P7973 ?latex . }
  OPTIONAL { ?item wdt:P1645 ?nist . }
  OPTIONAL { ?item wdt:P4732 ?goldbook . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
} 
GROUP BY ?item ?itemLabel ?itemDescription ?itemAltLabel ?value ?defining_formula
"""


def query_wikidata(sparql: str) -> List[Mapping[str, Any]]:
    """Query Wikidata's sparql service.

    Parameters
    ----------
    sparql :
        A SPARQL query string

    Returns
    -------
    :
        A list of bindings
    """
    logger.debug("running query: %s", sparql)
    res = requests.get(
        WIKIDATA_ENDPOINT, params={"query": sparql, "format": "json"}
    )
    res.raise_for_status()
    res_json = res.json()
    return res_json["results"]["bindings"]


def get_physical_constant_terms():
    """Get tuples for each constant."""
    records = query_wikidata(SPARQL)
    rv = []
    for record in records:
        label = record["itemLabel"]["value"].strip()
        if not label:
            continue

        try:
            description = record["itemDescription"]["value"]
        except KeyError:
            description = ""

        synonyms = [
            synonym.strip()
            for synonym in (
                record.get("itemAltLabel", {}).get("value") or ""
            ).split(",")
            if synonym.strip()
        ]

        # the actual number for the constant
        value = record["value"]["value"]
        formula = record["defining_formula"]["value"]
        symbols = [mathml for mathml in record["latexes"]["values"].split("|")]

        xrefs = []
        for key, prefix in [
            ("nists", "nist.codata"),
            ("goldbooks", "goldbook"),
        ]:
            if xref_values := record.get(key):
                for xref_value in xref_values["value"].split("|"):
                    xrefs.append(f"{prefix}:{xref_value}")

        rv.append(
            (
                record["item"]["value"][
                    len("http://www.wikidata.org/entity/") :
                ],
                label,
                description,
                synonyms,
                xrefs,
                value,
                formula,
                symbols,
            )
        )
    return rv


def update_physical_constants_resource():
    """Update a resource file with all physical constant names."""
    path = get_resource_path("physical_constants.tsv")
    names = sorted([row[1] for row in get_physical_constant_terms()])
    with open(path, "w") as file:
        file.write("\n".join(names))


if __name__ == "__main__":
    update_physical_constants_resource()
