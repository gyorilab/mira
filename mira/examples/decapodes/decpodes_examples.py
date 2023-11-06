from pathlib import Path

import requests

from mira.metamodel.decapodes import Decapode
from mira.sources.acsets.decapodes import process_decapode

ICE_DYNAMICS_EXAMPLE_JSON_URL = (
    "https://raw.githubusercontent.com/ciemss/Decapodes.jl"
    "/sa_climate_modeling/examples/climate/ice_dynamics.json"
)


HERE = Path(__file__).parent


def get_ice_dynamics_example() -> Decapode:
    """Return the ice dynamics example."""
    res_json = requests.get(ICE_DYNAMICS_EXAMPLE_JSON_URL).json()
    return process_decapode(res_json)
