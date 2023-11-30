"""Get terms from eiffel names."""

from typing import Collection, Mapping

import pystow
from pyobo import Term
from pyobo.struct import part_of
import pandas as pd

COUNTRIES_URL = "https://download.geonames.org/export/dump/countryInfo.txt"
ADMIN1_URL = "https://download.geonames.org/export/dump/admin1CodesASCII.txt"
ADMIN2_URL = "https://download.geonames.org/export/dump/admin2Codes.txt"
CITIES_URL = "https://download.geonames.org/export/dump/cities15000.zip"

ECV_KB_RDF_URL = ("https://raw.githubusercontent.com/benmomo/"
                  "eiffel-ontology/main/ontology/ecv-kb.ttl")
EO_TAXONOMY_RDF_URL = ("https://github.com/benmomo/eiffel-ontology/"
                       "blob/main/ontology/eo-kb.ttl")
SDG_GOALS_RDF_URL = ("https://raw.githubusercontent.com/benmomo/eiffel"
                     "-ontology/"
                     "main/ontology/sdg-kos-goals-targets-indicators.ttl")
SDG_SERIES_RDF_URL = ("https://raw.githubusercontent.com/benmomo/eiffel"
                      "-ontology/"
                      "main/ontology/sdg-kos-series-2019-Q2-G-01.ttl")

ECV_KB_CSV_INFO_URL = ("https://raw.githubusercontent.com/nanglo123/mira/"
                       "extract_eiffel_ontology/mira/dkg/resources/"
                       "sql_query_spreadsheet_results/ecv-kb%20information.csv")

ECV_KB_CSV_RELATION_URL = ("https://raw.githubusercontent.com/nanglo123/mira/"
                           "extract_eiffel_ontology/mira/dkg/resources/"
                           "sql_query_spreadsheet_results/ecv-kb%20"
                           "relation.csv")

EO_TAXONOMY_CSV_INFO_URL = ("https://raw.githubusercontent.com/nanglo123/mira/"
                            "extract_eiffel_ontology/mira/dkg/resources/"
                            "sql_query_spreadsheet_results/eo-kb%20"
                            "information.csv")

EO_TAXONOMY_CSV_RELATION_URL = ("https://raw.githubusercontent.com/nanglo123/"
                                "mira/extract_eiffel_ontology/mira/dkg/"
                                "resources/sql_query_spreadsheet_results/"
                                "eo-kb%20relation.csv")
SDG_GOALS_CSV_INFO_URL = ("https://raw.githubusercontent.com/nanglo123/mira/"
                          "extract_eiffel_ontology/mira/dkg/resources/"
                          "sql_query_spreadsheet_results/sdg-kos-goals-"
                          "targets-indicators%20information.csv")

SDG_GOALS_CSV_RELATION_URL = ("https://raw.githubusercontent.com/nanglo123/"
                              "mira/extract_eiffel_ontology/mira/dkg/"
                              "resources/sql_query_spreadsheet_results/sdg-"
                              "kos-goals-targets-indicators%20relation.csv")
SDG_SERIES_CSV_INFO_URL = ("https://raw.githubusercontent.com/nanglo123/mira/"
                           "extract_eiffel_ontology/mira/dkg/resources/sql_"
                           "query_spreadsheet_results/sdg-kos-series-"
                           "2019-Q2-G-01%20information.csv")
SDG_SERIES_CSV_RELATION_URL = ("https://raw.githubusercontent.com/nanglo123/"
                               "mira/extract_eiffel_ontology/mira/dkg/"
                               "resources/sql_query_spreadsheet_results/"
                               "sdg-kos-series-2019-Q2-G-01%20relation.csv")

PREDICATE_TYPEDEF_MAPPING = {

}


def get_eiffel_terms() -> Collection[Term]:
    ecv_info = get_info_curie_to_term(ECV_KB_CSV_INFO_URL)
    eo_info = get_info_curie_to_term(EO_TAXONOMY_CSV_INFO_URL)
    sdg_series_info = get_sdg_info_curie_to_term(SDG_SERIES_CSV_INFO_URL)
    sdg_goals_info = get_sdg_info_curie_to_term(SDG_GOALS_CSV_INFO_URL)


MODULE = pystow.module("mira", "eiffelnames")


# eiffelnames doesn't work as a prefix
def get_info_curie_to_term(url: str) -> Mapping[str, Term]:
    ecv_df = MODULE.ensure_csv(
        url=url,
        read_csv_kwargs=dict(
            dtype=str,
            keep_default_na=False,
            sep=','
        )
    )
    curie_to_term = {}
    for curie, uri, label, description in ecv_df.values:
        term = Term.from_triple("geonames", identifier=uri,
                                name=label,
                                definition=description)
        term.append_property('curie', curie)
        curie_to_term[curie] = term
    return curie_to_term


def get_sdg_info_curie_to_term(url: str) -> Mapping[str, Term]:
    ecv_df = MODULE.ensure_csv(
        url=url,
        read_csv_kwargs=dict(
            dtype=str,
            keep_default_na=False,
            sep=','
        )
    )
    curie_to_term = {}
    for curie, uri, label in ecv_df.values:
        term = Term.from_triple("geonames", identifier=uri,
                                name=label)
        term.append_property('curie', curie)
        curie_to_term[curie] = term
    return curie_to_term


def get_curie_to_relation(curie_to_term: Mapping[str, Term]):
    pass


def main():
    get_eiffel_terms()


if __name__ == "__main__":
    main()
