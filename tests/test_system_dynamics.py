import requests
from pathlib import Path

from mira.sources.system_dynamics.vensim import *
from mira.sources.system_dynamics.stella import *

MDL_SIR_URL = "https://raw.githubusercontent.com/SDXorg/test-models/master/samples/SIR/SIR.mdl"
XMILE_SIR_URL = "https://raw.githubusercontent.com/SDXorg/test-models/master/samples/SIR/SIR.xmile"
MDL_SIR_PATH = Path(__file__).parent / "SIR.mdl"
XMILE_SIR_PATH = Path(__file__).parent / "SIR.xmile"


def test_vensim_file():
    data = requests.get(MDL_SIR_URL).content
    with open(MDL_SIR_PATH, "wb") as file:
        file.write(data)
    tm = template_model_from_mdl_file(MDL_SIR_PATH)


def test_vensim_url():
    tm = template_model_from_mdl_url(MDL_SIR_URL)


def test_stella_file():
    data = requests.get(XMILE_SIR_URL).content
    with open(XMILE_SIR_PATH, "wb") as file:
        file.write(data)
    tm = template_model_from_stella_model_file(XMILE_SIR_PATH)


def test_stella_url():
    tm = template_model_from_stella_model_url(XMILE_SIR_URL)
