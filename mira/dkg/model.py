"""Modeling blueprint

This submodule serves as an API for modeling
"""
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Literal, Any, Set, Type, Union

import pystow
from fastapi import APIRouter, BackgroundTasks, FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from mira.metamodel import NaturalConversion, Template, ControlledConversion
from mira.modeling import Model, TemplateModel
from mira.modeling.gromet_model import GrometModel
from mira.modeling.ops import stratify
from mira.modeling.petri import PetriNetModel
from mira.modeling.viz import GraphicalModel

__all__ = [
    "model_blueprint",
]


viz_temp = pystow.module("mira", "tmp")


model_blueprint = APIRouter()


# PetriNetModel
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
    """Create a PetriNet model from a TemplateModel"""
    model = Model(template_model)
    petri_net = PetriNetModel(model)
    petri_net_json = petri_net.to_json()
    return petri_net_json


# GroMEt
class ToGrometQuery(BaseModel):
    model_name: str
    name: str
    template_model: TemplateModel


@model_blueprint.post("/to_gromet", response_model=Dict[str, Any])
def model_to_gromet(data: ToGrometQuery):
    """Create a GroMEt object from a TemplateModel"""
    model = Model(data.template_model)
    gromet_model = GrometModel(model, name=data.name, model_name=data.model_name)
    gromet_json = asdict(gromet_model.gromet_model)
    return gromet_json


# Model stratification
class StratificationQuery(BaseModel):
    template_model: TemplateModel
    key: str
    strata: Set[str]
    structure: Union[List[List[str]], None] = None
    directed: bool = False
    conversion_cls: Literal["natural_conversion", "controlled_conversion"] = "natural_conversion"

    def get_conversion_cls(self) -> Type[Template]:
        if self.conversion_cls == "natural_conversion":
            return NaturalConversion
        return ControlledConversion


@model_blueprint.post("/stratify", response_model=TemplateModel)
def model_stratification(stratification_query: StratificationQuery):
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


@model_blueprint.post("/viz/to_dot_file", response_class=FileResponse)
def model_to_viz_dot(template_model: TemplateModel, bg_task: BackgroundTasks):
    """Create a graphviz dot file from a TemplateModel"""
    return _graph_model(
        template_model=template_model,
        file_suffix="gv",
        file_format="dot",
        media_type="text/vnd.graphviz",
        background_tasks=bg_task,
    )


@model_blueprint.post("/viz/to_image")
def model_to_graph_image(template_model: TemplateModel, bg_task: BackgroundTasks):
    """Create a graph image from a TemplateModel"""
    return _graph_model(
        template_model=template_model,
        file_suffix="png",
        file_format="png",
        media_type="image/png",
        background_tasks=bg_task,
    )
