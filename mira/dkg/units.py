from textwrap import dedent
from typing import List, Mapping, Any
import logging
import requests
from .resources import get_resource_path

__all__ = [
    "get_unit_terms",
]

logger = logging.getLogger(__name__)

#: Wikidata SPARQL endpoint. See https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service#Interfacing
WIKIDATA_ENDPOINT = "https://query.wikidata.org/bigdata/namespace/wdq/sparql"

SPARQL = dedent("""\
    SELECT ?item ?itemLabel ?itemDescription ?umuc ?uo ?qudt
    WHERE 
    {
      ?item wdt:P7825 ?umuc .
      OPTIONAL { ?item wdt:P8769 ?uo }
      OPTIONAL { ?item wdt:P2968 ?qudt }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". } # Helps get the label in your language, if not, then en language
    }
""")


def query_wikidata(sparql: str) -> List[Mapping[str, Any]]:
    """Query Wikidata's sparql service.

    :param sparql: A SPARQL query string
    :return: A list of bindings
    """
    logger.debug("running query: %s", sparql)
    res = requests.get(WIKIDATA_ENDPOINT, params={"query": sparql, "format": "json"})
    res.raise_for_status()
    res_json = res.json()
    return res_json["results"]["bindings"]


def get_unit_terms():
    """Get tuples for each unit."""
    records = query_wikidata(SPARQL)
    rv = []
    for record in records:
        xrefs = []
        for prefix in [
            # "umuc",
            "qudt",
        ]:
            value = record.get(prefix)
            if value:
                xrefs.append(f"{prefix}:{value['value']}")
        try:
            description = record["itemDescription"]["value"]
        except KeyError:
            description = ""
        rv.append((
            record["item"]["value"][len("http://www.wikidata.org/entity/"):],
            record["itemLabel"]["value"],
            description,
            xrefs,
        ))
    return rv


def update_unit_names_resource():
    """Update a resource file with all unit names."""
    path = get_resource_path("unit_names.tsv")
    unit_names = sorted([unit_row[1] for unit_row in get_unit_terms()])
    with open(path, "w") as file:
        file.write("\n".join(unit_names))
