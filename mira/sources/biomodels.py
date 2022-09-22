"""
The BioModels database lists several high quality
models at https://www.ebi.ac.uk/biomodels/covid-19
that might be relevant for ingestion into the DKG.
"""

import json

import pandas as pd
import pystow
import requests
from pydantic.json import pydantic_encoder
from tabulate import tabulate
from tqdm import tqdm

from mira.modeling.viz import GraphicalModel
from mira.sources.sbml import template_model_from_sbml_file

MODULE = pystow.module("mira")
BIOMODELS = MODULE.module("biomodels")

SEARCH_URL = "https://www.ebi.ac.uk/biomodels/search"
DOWNLOAD_URL = "https://www.ebi.ac.uk/biomodels/search/download"

SPECIES_BLACKLIST = {
    "BIOMD0000000991": ["detected_cumulative"],
}


def main():
    """Iterate over COVID-19 models and parse them."""

    query_path = BIOMODELS.join(name="query.tsv")

    if query_path.is_file():
        df = pd.read_csv(query_path, sep="\t")
    else:
        models = []
        #: See API documentation at https://www.ebi.ac.uk/biomodels/docs/
        res = requests.get(
            SEARCH_URL,
            headers={"Accept": "application/json"},
            params={
                "query": "submitter_keywords:COVID-19",
                "domain": "biomodels",
                "numResults": 30,
            },
        ).json()
        models.extend(res.pop("models"))
        # TODO extend with pagination at same time as making query configurable

        # Split titles that have the AuthorYYYY - Title format
        for model in models:
            model_name = model.pop("name")
            if model_name == model["id"]:
                continue
            try:
                model_author, model_name = (s.strip() for s in model_name.split("-", 1))
            except ValueError:
                model["name"] = model_name
                continue
            else:
                model["name"] = model_name
                model["author"] = model_author

        df = pd.DataFrame(models).sort_values("id")
        df.to_csv(query_path, sep="\t", index=False)

    columns = ["id", "format", "author", "name"]
    rows = []
    for model_id, model_format, model_author, model_name in tqdm(
        df[columns].values, desc="Converting", unit="model"
    ):
        model_module = BIOMODELS.module("models", model_id)
        url = f"{DOWNLOAD_URL}?models={model_id}"
        if model_format == "SBML":
            with model_module.ensure_open_zip(
                url=url, name=f"{model_id}.zip", inner_path=f"{model_id}.xml"
            ) as file:
                try:
                    parse_result = template_model_from_sbml_file(
                        file, model_id=model_id, reporter_ids=SPECIES_BLACKLIST.get(model_id)
                    )
                except Exception as e:
                    tqdm.write(f"[{model_id}] failed to parse: {e}")
                    continue
            model_module.join(name=f"{model_id}.json").write_text(
                json.dumps(parse_result.template_model, indent=2, default=pydantic_encoder)
            )

            # Write a petri-net type graphical representation of the model
            m = GraphicalModel.from_template_model(parse_result.template_model)
            m.graph.graph_attr[
                "label"
            ] = f"{model_name}\n{model_id}\n{model_author[:-4]}, {model_author[-4:]}"
            m.write(model_module.join(name=f"{model_id}.png"))
            m.write(BIOMODELS.join("images", name=f"{model_id}.png"))

            rows.append(
                (
                    model_id,
                    model_name,
                    len(parse_result.template_model.templates),
                    ", ".join(sorted({t.type for t in parse_result.template_model.templates})),
                )
            )
        else:
            # tqdm.write(f"[{model_id}] unhandled model format: {model_format}")
            continue

    summary_columns = ["model_id", "name", "# templates", "template_types"]
    summary_df = pd.DataFrame(rows, columns=summary_columns).sort_values(
        "# templates", ascending=False
    )
    print(tabulate(summary_df, headers=summary_df.columns, showindex=False))


if __name__ == "__main__":
    main()
