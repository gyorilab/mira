"""
These tests are smoke tests to determine whether we can convert SBML Qual documents into MIRA
template models. They do not test for correctness.
"""
import requests

from mira.sources.sbml.qual_api import template_model_from_sbml_qual_string
from mira.sources.biomodels import get_sbml_model

models = ["Apoptosis"]
BASE_URL = "https://gitlab.lcsb.uni.lu/covid/models/-/raw/master/Executable%20Modules/SBML_qual_build/sbml"


def test_qual_models_from_example_repo():
    for model in models:
        url = f"{BASE_URL}/{model}_stable.sbml"
        xml_string = requests.get(url).text
        tm = template_model_from_sbml_qual_string(xml_string)


def test_qual_models_from_biomodels():
    model_ids = ["BIOMD0000000562"]
    # Full model list for reference
    #model_ids = ["BIOMD0000000562", "BIOMD0000000592", "BIOMD0000000593"]
    for model_id in model_ids:
        model_text = get_sbml_model(model_id)
        tm = template_model_from_sbml_qual_string(model_text)
