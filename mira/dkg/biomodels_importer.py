"""
The BioModels database lists several high quality
models at https://www.ebi.ac.uk/biomodels/covid-19
that might be relevant for ingestion into the DKG.

Alternate XPath queries for COPASI data:

1. ``copasi:COPASI/rdf:RDF/rdf:Description/bqbiol:hasProperty``
2. ``copasi:COPASI/rdf:RDF/rdf:Description/CopasiMT:is``
"""

import json

import bioregistry
import curies
import pandas as pd
import pystow
import requests
from libsbml import SBMLDocument, SBMLReader
from lxml import etree
from pydantic.json import pydantic_encoder
from tqdm import tqdm

from mira.metamodel import Concept, ControlledConversion, NaturalConversion
from mira.modeling import TemplateModel
from mira.modeling.viz import GraphicalModel

MODULE = pystow.module("mira")
BIOMODELS = MODULE.module("biomodels")

SEARCH_URL = "https://www.ebi.ac.uk/biomodels/search"
DOWNLOAD_URL = "https://www.ebi.ac.uk/biomodels/search/download"
PREFIX_MAP = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dcterms": "http://purl.org/dc/terms/",
    "vCard": "http://www.w3.org/2001/vcard-rdf/3.0#",
    "vCard4": "http://www.w3.org/2006/vcard/ns#",
    "bqbiol": "http://biomodels.net/biology-qualifiers/",
    "bqmodel": "http://biomodels.net/model-qualifiers/",
    "CopasiMT": "http://www.copasi.org/RDF/MiriamTerms#",
    "copasi": "http://www.copasi.org/static/sbml",
}
RESOURCE_KEY = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"
IDENTIFIERS_XPATH = f"rdf:RDF/rdf:Description/bqbiol:is/rdf:Bag/rdf:li"
PROPERTIES_XPATH = f"rdf:RDF/rdf:Description/bqbiol:hasProperty/rdf:Bag/rdf:li"

converter = curies.Converter.from_reverse_prefix_map(
    bioregistry.manager.get_reverse_prefix_map(include_prefixes=True)
)


def _parse(i: str):
    prefix, identifier = converter.parse_uri(i)
    return prefix, identifier


def handle_sbml_document(sbml_document: SBMLDocument) -> TemplateModel:
    # see docs on models
    # https://sbml.org/software/libsbml/5.18.0/docs/formatted/python-api/classlibsbml_1_1_s_b_m_l_document.html
    sbml_model = sbml_document.getModel()

    concepts = {}
    # see https://sbml.org/software/libsbml/5.18.0/docs/formatted/python-api/classlibsbml_1_1_species.html
    for species in sbml_model.getListOfSpecies():
        species_id = species.getId()
        name = species.getName()
        annotation_tree = etree.fromstring(species.getAnnotationString())

        rdf_properties = [
            _parse(desc.attrib[RESOURCE_KEY])
            for desc in annotation_tree.findall(PROPERTIES_XPATH, namespaces=PREFIX_MAP)
        ]
        identifiers = dict(
            converter.parse_uri(element.attrib[RESOURCE_KEY])
            for element in annotation_tree.findall(IDENTIFIERS_XPATH, namespaces=PREFIX_MAP)
        )
        concepts[species_id] = Concept(
            name=name,
            identifiers=identifiers,
            context={"property": ":".join(rdf_properties[0])} if rdf_properties else {},
        )

    templates = []
    # see docs on reactions
    # https://sbml.org/software/libsbml/5.18.0/docs/formatted/python-api/classlibsbml_1_1_reaction.html
    for reaction in sbml_model.getListOfReactions():
        modifiers = [concepts[modifier.getSpecies()] for modifier in reaction.getListOfModifiers()]
        reactants = [concepts[reactant.getSpecies()] for reactant in reaction.getListOfReactants()]
        products = [concepts[product.getSpecies()] for product in reaction.getListOfProducts()]
        if len(reactants) == 1 and len(products) == 1:
            if len(modifiers) == 0:
                template = NaturalConversion(
                    subject=reactants[0],
                    outcome=products[0],
                )
                templates.append(template)
            elif len(modifiers) == 1:
                template = ControlledConversion(
                    subject=reactants[0],
                    outcome=products[0],
                    controller=modifiers[0],
                )
                templates.append(template)
            else:
                tqdm.write(f"Skipping reaction with multiple modifiers: {modifiers}")
                continue
        else:
            tqdm.write(f"Skipping reaction with multiple inputs/outputs")
            continue

    return TemplateModel(templates=templates)


def main():
    """Iterate over COVID-19 models and parse them."""
    models = []

    res = requests.get(
        SEARCH_URL,
        headers={"Accept": "application/json"},
        params={
            "query": "submitter_keywords:COVID-19",
            "domain": "biomodels",
            "numResults": 40,
        },
    ).json()
    models.extend(res["models"])

    for model in models:
        name = model.pop("name")
        try:
            author, name = (s.strip() for s in name.split("-", 1))
        except ValueError:
            tqdm.write(f"could not parse {name}")
            continue
        else:
            model["name"] = name
            model["author"] = author
    df = pd.DataFrame(models)
    columns = ["id", "format", "author", "name"]
    for model_id, model_format, author, name in df[columns].values:
        url = f"{DOWNLOAD_URL}?models={model_id}"
        if model_format == "SBML":
            with BIOMODELS.ensure_open_zip(
                url=url, name=f"{model_id}.zip", inner_path=f"{model_id}.xml"
            ) as file:
                sbml_document = SBMLReader().readSBMLFromString(file.read().decode("utf-8"))
            template_model = handle_sbml_document(sbml_document)
            BIOMODELS.join(name=f"{model_id}.json").write_text(
                json.dumps(template_model, indent=2, default=pydantic_encoder)
            )
            m = GraphicalModel.from_template_model(template_model)
            m.graph.graph_attr["label"] = f"{name}\n{model_id}\n{author[:-4]}, {author[-4:]}"
            m.write(BIOMODELS.join(name=f"{model_id}.png"))
        else:
            tqdm.write(f"unhandled model format: {model_format}")
            continue


if __name__ == "__main__":
    main()
