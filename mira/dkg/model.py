"""Modeling blueprint

This submodule serves as an API for modeling
"""
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Literal, Any, Set, Type, Union

import pystow
from fastapi import APIRouter, BackgroundTasks, Body
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from mira.metamodel import NaturalConversion, Template, ControlledConversion
from mira.metamodel.ops import stratify
from mira.modeling import Model
from mira.metamodel.templates import TemplateModel
# from mira.modeling.gromet_model import GrometModel
from mira.modeling.petri import PetriNetModel
from mira.modeling.viz import GraphicalModel

__all__ = [
    "model_blueprint",
]


viz_temp = pystow.module("mira", "tmp")


model_blueprint = APIRouter()


# TemplateModel example
template_model_example = {
    "templates": [
        {
            "type": "ControlledConversion",
            "controller": {
                "name": "infected population",
                "identifiers": {"ido": "0000511"},
            },
            "subject": {
                "name": "susceptible population",
                "identifiers": {"ido": "0000514"},
            },
            "outcome": {
                "name": "infected population",
                "identifiers": {"ido": "0000511"},
            },
        },
        {
            "type": "NaturalConversion",
            "subject": {
                "name": "infected population",
                "identifiers": {"ido": "0000511"},
            },
            "outcome": {
                "name": "immune population",
                "identifiers": {"ido": "0000592"},
            },
        },
    ]
}


# PetriNetModel
States = List[Dict[Literal["sname"], str]]
Transitions = List[Dict[Literal["tname"], str]]
Inputs = List[Dict[Literal["is", "it"], int]]
Outputs = List[Dict[Literal["os", "ot"], int]]


class PetriNetResponse(BaseModel):
    S: States = Field(..., description="A list of states")  # States
    T: Transitions = Field(..., description="A list of transitions")  # Transitions
    I: Inputs = Field(..., description="A list of inputs")  # Inputs
    O: Outputs = Field(..., description="A list of outputs")  # Outputs


@model_blueprint.post("/to_petrinet", response_model=PetriNetResponse, tags=["modeling"])
def model_to_petri(template_model: TemplateModel = Body(..., example=template_model_example)):
    """Create a PetriNet model from a TemplateModel"""
    model = Model(template_model)
    petri_net = PetriNetModel(model)
    petri_net_json = petri_net.to_json()
    return petri_net_json


# GroMEt
# class ToGrometQuery(BaseModel):
#     """A query to generate a GroMet model from a TemplateModel"""
#
#     model_name: str = Field(description='The model name, e.g. "SIR"', example="SIR")
#     name: str = Field(
#         description='The name of the model, e.g. "my_sir_model"', example="sir_model_1"
#     )
#     template_model: TemplateModel = Field(
#         ...,
#         description="The template model to make a GroMEt model from",
#         example=template_model_example,
#     )
#
#
# @model_blueprint.post("/to_gromet", response_model=Dict[str, Any], tags=["modeling"])
# def model_to_gromet(
#     data: ToGrometQuery = Body(
#         ...,
#         example={
#             "model_name": "SIR",
#             "name": "sir_model_1",
#             "template_model": template_model_example,
#         },
#     )
# ):
#     """Create a GroMEt object from a TemplateModel"""
#     model = Model(data.template_model)
#     gromet_model = GrometModel(model, name=data.name, model_name=data.model_name)
#     gromet_json = asdict(gromet_model.gromet_model)
#     return gromet_json


# Model stratification
class StratificationQuery(BaseModel):
    template_model: TemplateModel = Field(
        ..., description="The template model to stratify", example=template_model_example
    )
    key: str = Field(..., description="The (singular) name of the stratification", example="city")
    strata: Set[str] = Field(
        ..., description="A list of the values for stratification", example=["boston", "nyc"]
    )
    structure: Union[List[List[str]], None] = Field(
        None,
        description="An iterable of pairs corresponding to a directed network "
        "structure where each of the pairs has two strata. If none given, "
        "will assume a complete network structure.",
        example=[["boston", "nyc"]],
    )
    directed: bool = Field(
        False, description="Whether the model has directed edges or not.", example=True
    )
    conversion_cls: Literal["natural_conversion", "controlled_conversion"] = Field(
        "natural_conversion",
        description="The template class to be used for conversions between strata defined by the network structure.",
        example="natural_conversion",
    )

    def get_conversion_cls(self) -> Type[Template]:
        if self.conversion_cls == "natural_conversion":
            return NaturalConversion
        return ControlledConversion


@model_blueprint.post("/stratify", response_model=TemplateModel, tags=["modeling"])
def model_stratification(
    stratification_query: StratificationQuery = Body(
        ...,
        example={
            "template_model": template_model_example,
            "key": "city",
            "strata": ["boston", "nyc"],
        },
    )
):
    """Stratify a model according to the specified stratification"""
    template_model = stratify(
        template_model=stratification_query.template_model,
        key=stratification_query.key,
        strata=stratification_query.strata,
        structure=stratification_query.structure,
        directed=stratification_query.directed,
        conversion_cls=stratification_query.get_conversion_cls(),
    )
    return template_model


# GraphicalModel endpoints
def _delete_after_response(tmp_file: Union[str, Path]):
    Path(tmp_file).unlink(missing_ok=True)


def _graph_model(
    template_model: TemplateModel,
    file_suffix: str,
    file_format: str,
    media_type: str,
    background_tasks: BackgroundTasks,
):
    # Get GraphicalModel
    mm = Model(template_model)
    gm = GraphicalModel(mm)

    # Save
    fo = viz_temp.join(name=f"{uuid.uuid4()}.{file_suffix}")
    posix_str = fo.absolute().as_posix()

    # Make sure the file is always deleted, even if there is an error
    try:
        gm.write(path=posix_str, format=file_format)
    except Exception as exc:
        raise exc
    finally:
        background_tasks.add_task(_delete_after_response, fo)

    # Send back file to client
    return FileResponse(
        path=posix_str, media_type=media_type, filename=f"model_graph.{file_suffix}"
    )


@model_blueprint.post(
    "/viz/to_dot_file",
    response_class=FileResponse,
    response_description="A successful response returns a grapviz dot file of the provided TemplateModel",
    tags=["modeling"],
)
def model_to_viz_dot(
    bg_task: BackgroundTasks,
    template_model: TemplateModel = Body(..., example=template_model_example),
):
    """Create a graphviz dot file from a TemplateModel"""
    return _graph_model(
        template_model=template_model,
        file_suffix="gv",
        file_format="dot",
        media_type="text/vnd.graphviz",
        background_tasks=bg_task,
    )


@model_blueprint.post(
    "/viz/to_image",
    response_class=FileResponse,
    response_description="A successful response returns a png image of the "
    "graph representation of the provided TemplateModel",
    tags=["modeling"],
)
def model_to_graph_image(
    bg_task: BackgroundTasks,
    template_model: TemplateModel = Body(..., example=template_model_example),
):
    """Create a graph image from a TemplateModel"""
    return _graph_model(
        template_model=template_model,
        file_suffix="png",
        file_format="png",
        media_type="image/png",
        background_tasks=bg_task,
    )
