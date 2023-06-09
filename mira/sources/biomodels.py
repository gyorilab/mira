"""
The BioModels database lists several high quality
models at https://www.ebi.ac.uk/biomodels/covid-19.
"""
import io
import zipfile

import pystow
import requests
from tabulate import tabulate
from tqdm import tqdm

from mira.metamodel import TemplateModel
from mira.modeling.viz import GraphicalModel
from mira.sources.sbml import (
    template_model_from_sbml_file_obj,
    template_model_from_sbml_string,
)

MODULE = pystow.module("mira")
BIOMODELS = MODULE.module("biomodels")

SEARCH_URL = "https://www.ebi.ac.uk/biomodels/search"
DOWNLOAD_URL = "https://www.ebi.ac.uk/biomodels/search/download"

SPECIES_BLACKLIST = {
    "BIOMD0000000991": ["detected_cumulative"],
    "BIOMD0000000957": ["Confirmed"],
    "BIOMD0000000960": ["Cumulative_Cases"],
    # "BIOMD0000000970": ["Total_Population"],
}

#: Additional model identifiers for epidemiology models that
#: do not appear in the BioModels curated list of COVID-19 models
NON_COVID_EPI_MODELS = {
    "BIOMD0000000715",  # SEIS epidemic model with the impact of media
    "BIOMD0000001045",  # hong kong flu
    "MODEL1805220001",  # Human/Mosquito SEIR/SEI Mode
    "MODEL1805230001",  # Model for HIV-Malaria co-infection
    "MODEL1808280006",  # SIRWS model with immune boosting and cross-immunity between two pathogens
    "MODEL1008060002",  # zombie infection toy model (lol)
    "BIOMD0000000922",
    "BIOMD0000000726",
    "BIOMD0000000249",
    "BIOMD0000000294",
    "BIOMD0000000716",
    "BIOMD0000000717",
    "MODEL1008060000",
    "MODEL2212310001",
    "MODEL1808280011",
    "BIOMD0000000950",
    "BIOMD0000000949",
}
MODEL_BLACKLIST = {
    "MODEL2209020001",  # Trash BEL model from Fraunhofer
    "MODEL2003020001",  # only has OMEX data
}
#: Annotation of missing pubmeds to model ids
MODEL_TO_PUBMED = {
    "BIOMD0000000716": "30839942",
    "BIOMD0000000717": "30839942",
}


def query_biomodels(
    query: str = "submitter_keywords:COVID-19",
    limit: int = 30,
):
    """Query and paginate over results from the BioModels API.

    .. seealso:: https://www.ebi.ac.uk/biomodels/docs/
    """
    model_ids = set()
    res = requests.get(
        SEARCH_URL,
        headers={"Accept": "application/json"},
        params={
            "query": query,
            "domain": "biomodels",
            "numResults": limit,
        },
    ).json()
    model_ids.update(
        model['id']
        for model in res.pop("models")
    )
    model_ids.update(NON_COVID_EPI_MODELS)
    model_ids.difference_update(MODEL_BLACKLIST)

    # TODO extend with pagination at same time as making query configurable

    rv = []
    # Split titles that have the AuthorYYYY - Title format
    for model_id in model_ids:
        model = {"biomodels_id": model_id}
        model_metadata = requests.get(
            f"https://www.ebi.ac.uk/biomodels/{model_id}",
            headers={"Accept": "application/json"},
        ).json()
        publication_link = model_metadata.get("publication", {}).get("link")
        if publication_link:
            if model_id in MODEL_TO_PUBMED:
                model["pubmed"] = MODEL_TO_PUBMED[model_id]
            elif "identifiers.org/pubmed/" in publication_link:
                model["pubmed"] = publication_link.split("/")[-1]
            elif publication_link.startswith("http://identifiers.org/doi/"):
                model["doi"] = publication_link[len("http://identifiers.org/doi/"):]
            elif publication_link.startswith("https://doi.org/"):
                model["doi"] = publication_link[len("https://doi.org/"):]
            else:
                tqdm.write(f"[{model_id}] unhandled publication link: {publication_link}")
        model_name = model_metadata.get("name")
        if model_name == model_id:
            continue
        try:
            model_author, model_name = (s.strip() for s in model_name.split(" - ", 1))
        except ValueError:
            model["name"] = model_name
            continue
        else:
            model["name"] = model_name
            model["author"] = model_author[:-4]
            model["year"] = model_author[-4:]
        rv.append(model)
    return rv


def get_sbml_model(model_id: str) -> str:
    """Return the SBML string content for a BioModels model from the web.

    Parameters
    ----------
    model_id :
        The BioModels ID of the model.

    Returns
    -------
    :
        The SBML XML string corresponding to the model.
    """
    url = f'{DOWNLOAD_URL}?models={model_id}'
    res = requests.get(url)
    if res.status_code == 404:
        raise FileNotFoundError(f'No such file on source server: {model_id}')
    z = zipfile.ZipFile(io.BytesIO(res.content))
    return z.open(f'{model_id}.xml').read().decode('utf-8')


def get_template_model(model_id: str) -> TemplateModel:
    """Return the Template Model processed from a BioModels model from the web.

    Parameters
    ----------
    model_id :
        The BioModels ID of the model.

    Returns
    -------
    :
        The Template model corresponding to the BioModels model.
    """
    sbml_xml = get_sbml_model(model_id)
    template_model = template_model_from_sbml_string(sbml_xml)
    return template_model


def main():
    """Iterate over COVID-19 models and parse them."""
    import pandas as pd
    from modeling.triples import TriplesGenerator

    triples_path = BIOMODELS.join(name="triples.tsv")
    query_path = BIOMODELS.join(name="query.tsv")
    if query_path.is_file():
        df = pd.read_csv(query_path, sep="\t")
    else:
        models = query_biomodels("submitter_keywords:COVID-19", limit=30)
        df = pd.DataFrame(models).sort_values(["year", "author", "name"]).reset_index()
        df = df[["biomodels_id", "name", "author", "year", "pubmed", "doi"]]
        df.to_csv(query_path, sep="\t", index=False)

    rows = []
    dataframes = []
    for model_id, model_name, model_author, model_year, pubmed, doi in tqdm(
        df.values, desc="Converting", unit="model"
    ):
        model_module = BIOMODELS.module("models", model_id)
        url = f"{DOWNLOAD_URL}?models={model_id}"
        with model_module.ensure_open_zip(
            url=url, name=f"{model_id}.zip", inner_path=f"{model_id}.xml"
        ) as file:
            try:
                template_model = template_model_from_sbml_file_obj(
                    file, model_id=model_id, reporter_ids=SPECIES_BLACKLIST.get(model_id)
                )
            except Exception as e:
                tqdm.write(f"[{model_id}] failed to parse: {e}")
                continue
        model_module.join(name=f"{model_id}.json").write_text(
            template_model.json(indent=2)
        )

        # Write a petri-net type graphical representation of the model
        m = GraphicalModel.from_template_model(template_model)
        m.graph.graph_attr[
            "label"
        ] = f"{model_name}\n{model_id}\n{model_author}, {model_year}"
        m.write(model_module.join(name=f"{model_id}.png"))
        m.write(BIOMODELS.join("images", name=f"{model_id}.png"))

        m = TriplesGenerator(template_model, skip_prefixes=["biomodel.species"])
        triples_df = m.to_dataframe()
        triples_df["model"] = model_id
        dataframes.append(triples_df)

        rows.append(
            (
                model_id,
                model_name,
                len(template_model.templates),
                ", ".join(sorted({t.type for t in template_model.templates})),
            )
        )

    cat_triples_df = pd.concat(dataframes)
    cat_triples_df.to_csv(triples_path, sep="\t", index=False)

    summary_columns = ["model_id", "name", "# templates", "template_types"]
    summary_df = pd.DataFrame(rows, columns=summary_columns).sort_values(
        "# templates", ascending=False
    )
    print(tabulate(summary_df, headers=summary_df.columns, showindex=False))


if __name__ == "__main__":
    main()
