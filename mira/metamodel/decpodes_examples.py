import json

import requests
from bs4 import BeautifulSoup

from .decapodes import Decapode


ICE_DYNAMICS_EXAMPLE_JSON_URL = (
    "https://raw.githubusercontent.com/ciemss/Decapodes.jl"
    "/sa_climate_modeling/examples/climate/ice_dynamics.json"
)
COMPOSITE_EXAMPLE_JSON_URL = (
    "https://algebraicjulia.github.io/SyntacticModels.jl/dev/generated"
    "/composite_models_examples/"
)


def get_ice_dynamics_example() -> Decapode:
    """Return the ice dynamics example."""
    res_json = requests.get(ICE_DYNAMICS_EXAMPLE_JSON_URL).json()
    return Decapode(res_json)


def get_composite_example_json() -> Decapode:
    # Det decapode json is in a code block in the page
    # The full xpath is: /html/body/div[1]/div[1]/article/pre[20]/code
    bs = BeautifulSoup(
        requests.get(COMPOSITE_EXAMPLE_JSON_URL).content,"html.parser"
    )
    code_block = bs.find_all("pre")[19]
    return json.loads(code_block.text)


# todo: the Decapode class currently assumes Decapode JSON, the composite
#  example contains DecaExpr
# def get_composite_example() -> Decapode:
#     """Return the composite example."""
#     example_json = get_composite_example_json()
#     return Decapode(example_json)
