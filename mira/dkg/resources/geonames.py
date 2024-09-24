"""Get terms from geonames."""

from typing import Collection, Mapping

import pystow
from pyobo import Term
from pyobo.struct import part_of
import pandas as pd

__all__ = ["get_geonames_terms"]

MODULE = pystow.module("mira", "geonames")
COUNTRIES_URL = "https://download.geonames.org/export/dump/countryInfo.txt"
ADMIN1_URL = "https://download.geonames.org/export/dump/admin1CodesASCII.txt"
ADMIN2_URL = "https://download.geonames.org/export/dump/admin2Codes.txt"
CITIES_URL = "https://download.geonames.org/export/dump/cities15000.zip"


def get_geonames_terms() -> Collection[Term]:
    code_to_country = get_code_to_country()
    code_to_admin1 = get_code_to_admin1(code_to_country)
    code_to_admin2 = get_code_to_admin2(code_to_admin1)
    cities = get_cities(
        code_to_country=code_to_country,
        code_to_admin1=code_to_admin1,
        code_to_admin2=code_to_admin2,
    )
    terms = cities.values()
    return terms


def get_code_to_country() -> Mapping[str, Term]:
    countries_df = MODULE.ensure_csv(
        url=COUNTRIES_URL,
        read_csv_kwargs=dict(
            skiprows=49,
            keep_default_na=False,  # NA is a country code
            dtype=str,
        ),
    )
    reorder = ["geonameid", *(c for c in countries_df.columns if c != "geonameid")]
    countries_df = countries_df[reorder]
    code_to_country = {}
    cols = ["geonameid", "Country", "#ISO"]
    for identifier, name, code in countries_df[cols].values:
        term = Term.from_triple("geonames", identifier, name)
        term.append_property("code", code)
        code_to_country[code] = term
    return code_to_country


def get_code_to_admin1(code_to_country: Mapping[str, Term]) -> Mapping[str, Term]:
    admin1_df = MODULE.ensure_csv(
        url=ADMIN1_URL,
        read_csv_kwargs=dict(
            header=None,
            names=["code", "name", "asciiname", "geonames_id"],
            dtype=str,
        ),
    )
    code_to_admin1 = {}
    cols = ["geonames_id", "name", "code"]
    for identifier, name, code in admin1_df[cols].values:
        term = Term.from_triple("geonames", identifier, name)
        term.append_property("code", code)
        code_to_admin1[code] = term

        country_code = code.split('.')[0]
        country_term = code_to_country[country_code]
        term.append_relationship(part_of, country_term)
    return code_to_admin1


def get_code_to_admin2(code_to_admin1: Mapping[str, Term]) -> Mapping[str, Term]:
    admin2_df = MODULE.ensure_csv(
        url=ADMIN2_URL,
        read_csv_kwargs=dict(
            header=None,
            names=["code", "name", "asciiname", "geonames_id"],
            dtype=str,
        ),
    )
    code_to_admin2 = {}
    for identifier, name, code in admin2_df[["geonames_id", "name", "code"]].values:
        term = Term.from_triple("geonames", identifier, name)
        term.append_property("code", code)
        code_to_admin2[code] = term

        admin1_code = code.rsplit('.', 1)[0]
        admin1_term = code_to_admin1[admin1_code]
        term.append_relationship(part_of, admin1_term)
    return code_to_admin2


def get_cities(code_to_country, code_to_admin1, code_to_admin2, *, minimum_population: int = 100_000):
    columns = [
        "geonames_id", "name", "asciiname", "synonyms",
        "latitude", "longitude", "feature_class", "feature_code", "country_code", "cc2",
        "admin1", "admin2", "admin3", "admin4",
        "population", "elevation", "dem", "timezone", "date_modified"
    ]
    cities_df = pystow.ensure_zip_df(
        "mira", "geonames",
        url=CITIES_URL, inner_path="cities15000.txt",
        read_csv_kwargs=dict(
            header=None,
            names=columns,
            dtype=str,
        ),
    )

    cities_df.synonyms = cities_df.synonyms.str.split(",")

    terms = {}
    for term in code_to_country.values():
        terms[term.identifier] = term
    cols = ["geonames_id", "name", "synonyms", "country_code", "admin1",
            "admin2", "population"]
    for identifier, name, synonyms, country, admin1, admin2, population in (cities_df[cols].values):
        if synonyms and not isinstance(synonyms, float):
            for synoynm in synonyms:
                term.append_synonym(synoynm)

        if pd.isna(admin1):
            print(f"[geonames:{identifier}] missing admin 1 code for {name} ({country})")
            continue

        admin1_full = f"{country}.{admin1}"
        admin1_term = code_to_admin1.get(admin1_full)
        if admin1_term is None:
            print("could not find admin1", admin1_full)
            continue

        terms[admin1_term.identifier] = admin1_term

        # We skip cities that don't meet the minimum population requirement
        if int(population) < minimum_population:
            continue
        terms[identifier] = term = Term.from_triple("geonames", identifier,
                                                    name)
        if pd.notna(admin2):
            admin2_full = f"{country}.{admin1}.{admin2}"
            admin2_term = code_to_admin2.get(admin2_full)
            if admin2_term is None or admin1_term is None:
                pass
                # print("could not find admin2", admin2_full)
            else:
                term.append_relationship(part_of, admin2_term)
                terms[admin2_term.identifier] = admin2_term

        else:  # pd.notna(admin1):
            # If there's no admin 2, just annotate directly onto admin 1
            term.append_relationship(part_of, admin1_term)

    return terms
