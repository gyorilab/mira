"""Modeling blueprint

This submodule serves as an API for modeling
"""
from typing import List, Dict, Literal

from fastapi import APIRouter
from pydantic import BaseModel

from mira.modeling import Model, TemplateModel
from mira.modeling.petri import PetriNetModel

__all__ = [
    "model_blueprint",
]


model_blueprint = APIRouter()


# PetriNetModel utils
States = List[Dict[Literal["sname"], str]]
Transitions = List[Dict[Literal["tname"], str]]
Inputs = List[Dict[Literal["is", "it"], int]]
Outputs = List[Dict[Literal["os", "ot"], int]]


class PetriNetResponse(BaseModel):
    S: States  # States
    T: Transitions  # Transitions
    I: Inputs  # Inputs
    O: Outputs  # Outputs


@model_blueprint.post("/to_petrinet", response_model=PetriNetResponse)
def model_to_petri(template_model: TemplateModel):
    model = Model(template_model)
    petri_net = PetriNetModel(model)
    petri_net_json = petri_net.to_json()
    return petri_net_json
