import json
from pathlib import Path

import requests

from mira.metamodel.decapodes import Decapode
from mira.sources.acsets.decapodes import process_decapode

ICE_DYNAMICS_EXAMPLE_JSON_URL = (
    "https://raw.githubusercontent.com/ciemss/Decapodes.jl"
    "/sa_climate_modeling/examples/climate/ice_dynamics.json"
)


HERE = Path(__file__).parent
EXAMPLES = HERE / "decapodes_vs_decaexpr_composite"
DECAPODE_OSCILLATOR = EXAMPLES / "d1_oscillator_decapode.json"
DECAPODE_FRICTION = EXAMPLES / "d2_friction_decapode.json"
DECAEXPR_OSCILLATOR = EXAMPLES / "oscillator_decaexpr.json"
DECAEXPR_FRICTION = EXAMPLES / "friction_decaexpr.json"


def get_ice_dynamics_example() -> Decapode:
    """Return the ice dynamics decapode example"""
    res_json = requests.get(ICE_DYNAMICS_EXAMPLE_JSON_URL).json()
    return process_decapode(res_json)


def get_oscillator_decapode() -> Decapode:
    """Return the oscillator decapode example"""
    with open(DECAPODE_OSCILLATOR) as f:
        decapode_osc_json = json.load(f)
        return process_decapode(decapode_osc_json)


def get_friction_decapode() -> Decapode:
    """Return the friction decaexpr example"""
    with open(DECAPODE_FRICTION) as f:
        decapode_friction_json = json.load(f)
        return process_decapode(decapode_friction_json)


def get_oscillator_decaexpr() -> Decapode:
    """Return the oscillator decaexpr example"""
    with open(DECAEXPR_OSCILLATOR) as f:
        decapode_osc_json = json.load(f)
        return process_decapode(decapode_osc_json)


def get_friction_decaexpr() -> Decapode:
    """Return the friction decaexpr example"""
    with open(DECAEXPR_FRICTION) as f:
        decapode_friction_json = json.load(f)
        return process_decapode(decapode_friction_json)
