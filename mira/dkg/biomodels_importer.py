"""
The BioModels database lists several high quality
models at https://www.ebi.ac.uk/biomodels/covid-19
that might be relevant for ingestion into the DKG.
"""

import pystow
import zipfile
import requests
import pandas as pd
from libsbml import SBMLReader

MODULE = pystow.module("mira")
BIOMODELS = MODULE.module("biomodels")

SEARCH_URL = "https://www.ebi.ac.uk/biomodels/search"
DOWNLOAD_URL = "https://www.ebi.ac.uk/biomodels/search/download"


def parse_sbml(x):
    return SBMLReader().readSBML(x)


def main():
    """Iterate over COVID-19 models and parse them."""
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
    # print(tabulate(df[columns], headers=columns, showindex=False))

    for model_id, model_format in df[["id", "format"]].values:
        url = f"{DOWNLOAD_URL}?models={model_id}"
        if model_format == "SBML":
            # tree = BIOMODELS.ensure_zip_xml(url=url, name=f"{model_id}.zip", inner_path=f"{model_id}.xml")
            with BIOMODELS.ensure_open_zip(url=url, name=f"{model_id}.zip", inner_path=f"{model_id}.xml") as file:
                sbml_document = SBMLReader().readSBMLFromString(file.read().decode("utf-8"))
            print(sbml_document)
        elif model_format == "COMBINE archive":
            # with BIOMODELS.ensure_open_zip(url=url, name=f"{model_id}.zip", inner_path=f"{model_id}.omex") as file:
            continue


if __name__ == '__main__':
    main()
