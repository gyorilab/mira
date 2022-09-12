"""Modeling blueprint

This submodule serves as an API for modeling
"""
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import List, Dict, Literal, Any, Set, Optional, Tuple, Type, Union

import pystow
from fastapi import APIRouter, BackgroundTasks
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


# GroMEt
class ToGrometQuery(BaseModel):
    model_name: str
    name: str
    template_model: TemplateModel


@model_blueprint.post("/to_gromet", response_model=Dict[str, Any])
def model_to_gromet(data: ToGrometQuery):
    model = Model(data.template_model)
    gromet_model = GrometModel(model, name=data.name, model_name=data.model_name)
    gromet_json = asdict(gromet_model.gromet_model)
    return gromet_json


# Model stratification
class StratificationQuery(BaseModel):
    template_model: TemplateModel
    key: str
    strata: Set[str]
    structure: Optional[List[Tuple[str, str]]] = None
    directed: bool = False
    conversion_cls: Literal["natural_conversion", "controlled_conversion"] = "natural_conversion"

    def get_conversion_cls(self) -> Type[Template]:
        if self.conversion_cls == "natural_conversion":
            return NaturalConversion
        return ControlledConversion


@model_blueprint.post("/stratify", response_model=TemplateModel)
def model_stratification(stratification_query: StratificationQuery):
    template_model = stratify(
        template_model=stratification_query.template_model,
        key=stratification_query.key,
        strata=stratification_query.strata,
        structure=stratification_query.structure,
        directed=stratification_query.directed,
        conversion_cls=stratification_query.get_conversion_cls(),
    )
    return template_model


def _delete_after_response(tmp_file: Union[str, Path]):
    Path(tmp_file).unlink(missing_ok=True)


@model_blueprint.post("/viz/to_dot_file", response_class=FileResponse)
def model_to_viz_dot(template_model: TemplateModel, bg_task: BackgroundTasks):
    # Get GraphicalModel
    mm = Model(template_model)
    gm = GraphicalModel(mm)

    # Save
    fo = viz_temp.join(name=f"{uuid.uuid4()}.gv")
    posix_str = fo.absolute().as_posix()

    # Make sure the file is always deleted, even if there is an error
    try:
        gm.write(path=posix_str, format="dot")
    except Exception as exc:
        raise exc
    finally:
        # Delete once file is sent
        bg_task.add_task(_delete_after_response, fo)

    # Send back file to client
    return FileResponse(
        path=posix_str, media_type="text/vnd.graphviz", filename="model_graph.gv"
    )


@model_blueprint.post("/viz/to_image")
def model_to_graph_image(template_model: TemplateModel, bg_task: BackgroundTasks):
    # Get GraphicalModel
    mm = Model(template_model)
    gm = GraphicalModel(mm)

    # Save
    fo = viz_temp.join(name=f"{uuid.uuid4()}.png")
    posix_str = fo.absolute().as_posix()

    # Make sure the file is always deleted, even if there is an error
    try:
        gm.write(path=posix_str, format="png")
    except Exception as exc:
        raise exc
    finally:
        # Delete once file is sent
        bg_task.add_task(_delete_after_response, fo)

    # Send back file to client
    return FileResponse(
        path=posix_str, media_type="image/png", filename="model_graph.png"
    )
