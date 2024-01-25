import requests
from pathlib import Path

from mira.sources.system_dynamics.vensim import *
from mira.sources.system_dynamics.stella import *

SIR_URL = "https://raw.githubusercontent.com/SDXorg/test-models/master/samples/SIR/SIR.mdl"
SIR_PATH = Path(__file__).parent / "SIR.mdl"


def test_vensim_file():
    data = requests.get(SIR_URL).content
    with open(SIR_PATH, "wb") as file:
        file.write(data)

    tm = template_model_from_mdl_file(SIR_PATH)


def test_vensim_url():
    tm = template_model_from_mdl_url(SIR_URL)


def test_stella_file():
    pass


def test_stella_url():
    pass
