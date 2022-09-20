"""
The BioModels database lists several high quality
models at https://www.ebi.ac.uk/biomodels/covid-19
that might be relevant for ingestion into the DKG.
"""

from tabulate import tabulate
import pystow
import requests
import pandas as pd

MODULE = pystow.module("mira")
BIOMODELS = MODULE.module("biomodeles")

SEARCH_URL = "https://www.ebi.ac.uk/biomodels/search"


def main():
    models = []

    res = requests.get(SEARCH_URL, headers={"Accept": "application/json"}, params={
        "query": "submitter_keywords:COVID-19",
        "domain": "biomodels",
        "numResults": 40,
    }).json()
    models.extend(res["models"])

    for model in models:
        name = model.pop("name")
        try:
            author, name = (s.strip() for s in name.split("-", 1))
        except ValueError:
            print(name)
            continue
        else:
            model["name"] = name
            model["author"] = author
    df = pd.DataFrame(models)
    columns = ["id", "format", "author", "name"]
    print(tabulate(df[columns], headers=columns, showindex=False))


if __name__ == '__main__':
    main()
