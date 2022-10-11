"""Modeling blueprint

This submodule serves as an API for modeling
"""
import uuid
from pathlib import Path
from typing import List, Dict, Literal, Set, Type, Union, Any

import pystow
from fastapi import APIRouter, BackgroundTasks, Body, Path as FastPath, \
    HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from mira.examples.sir import sir_bilayer
from mira.metamodel import NaturalConversion, Template, ControlledConversion
from mira.metamodel.ops import stratify
from mira.modeling import Model
from mira.metamodel.templates import TemplateModel
from mira.modeling.bilayer import BilayerModel
from mira.modeling.petri import PetriNetModel
from mira.modeling.viz import GraphicalModel
from mira.sources.bilayer import template_model_from_bilayer
from mira.sources.sbml import template_model_from_sbml_string
from mira.sources.biomodels import get_sbml_model

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
States = List[Dict[Literal["sname", "mira_ids", "mira_context"],
                   Union[str, None]]]
Transitions = List[Dict[Literal["tname", "template_type",
                                "parameter_name", "parameter_value"],
                        Union[str, float, None]]]
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


@model_blueprint.get(
    "/biomodels/{model_id}",
    response_model=TemplateModel,
    tags=["modeling"],
    status_code=200,
    responses={
        400: {
            "description": "Bad Request. When the model id doesn't match a "
                           "model, a bad request status will be returned."
        }
    },
)
def biomodels_id_to_model(
    model_id: str = FastPath(
        ...,
        description="The BioModels model ID to get the template model for.",
        example="BIOMD0000000956",
    ),
):
    """Get a BioModels base template model by providing its model id"""
    try:
        xml_string = get_sbml_model(model_id=model_id)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Bad model id")
    parse_res = template_model_from_sbml_string(xml_string, model_id=model_id)
    return parse_res.template_model


@model_blueprint.post("/bilayer_to_model", response_model=TemplateModel, tags=["modeling"])
def bilayer_to_template_model(
    bilayer: Dict[str, Any] = Body(
        ...,
        description="The bilayer json to transform to a template model",
        example=sir_bilayer,
    )
):
    """Transform a bilayer json to a template model"""
    # todo: Create model for bilayer
    return template_model_from_bilayer(bilayer_json=bilayer)


@model_blueprint.post("/model_to_bilayer", response_model=Dict[str, Any], tags=["modeling"])
def template_model_to_bilayer(
    template_model: TemplateModel = Body(
        ...,
        description="A template model to turn into a bilayer json",
        example=template_model_example,
    )
):
    """Turn template model into a bilayer json"""
    # todo: Use model for bilayer to be used from above as response model
    bilayer_model = BilayerModel(Model(template_model))
    return bilayer_model.bilayer


class XmlString(BaseModel):
    xml_string: str = Field(..., description="An SBML model as an XML string")


@model_blueprint.post("/sbml_xml_to_model", response_model=TemplateModel, tags=["modeling"])
def sbml_xml_to_model(
    xml: XmlString = Body(..., description="An XML string to turn into a template model")
):
    """Turn SBML XML into a template model"""
    parse_res = template_model_from_sbml_string(xml.xml_string)
    return parse_res.template_model


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
