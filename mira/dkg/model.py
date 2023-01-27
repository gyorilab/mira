"""Modeling blueprint

This submodule serves as an API for modeling
"""
import uuid
from pathlib import Path
from typing import List, Dict, Literal, Set, Type, Union, Any, Optional, Tuple

import pystow
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Path as FastPath,
    HTTPException,
    Query,
    Request,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from mira.dkg.utils import DKG_REFINER_RELS
from mira.examples.sir import sir_bilayer, sir
from mira.metamodel import NaturalConversion, Template, ControlledConversion
from mira.metamodel.ops import stratify
from mira.modeling import Model
from mira.metamodel.templates import TemplateModel, TemplateModelDelta, \
    Concept, Parameter, ModelComparisonGraphdata
from mira.metamodel.ops import simplify_rate_laws, aggregate_parameters
from mira.modeling.bilayer import BilayerModel
from mira.modeling.petri import PetriNetModel
from mira.modeling.viz import GraphicalModel
from mira.sources.bilayer import template_model_from_bilayer
from mira.sources.petri import template_model_from_petri_json
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
template_model_example_w_context = TemplateModel(
    templates=[
        t.with_context(location="geonames:5128581")
        for t in TemplateModel(**template_model_example).templates
    ]
)


# PetriNetModel
States = List[Dict[Literal["sname", "mira_ids", "mira_context",
                           "mira_initial_value"],
                   Union[str, float, None]]]
Transitions = List[Dict[Literal["tname", "template_type",
                                "parameter_name", "parameter_value"],
                        Union[str, float, None]]]
Inputs = List[Dict[Literal["is", "it"], int]]
Outputs = List[Dict[Literal["os", "ot"], int]]

# PetriNetModel json example
petrinet_json = PetriNetModel(Model(sir)).to_json()


class PetriNetResponse(BaseModel):
    S: States = Field(..., description="A list of states")  # States
    T: Transitions = Field(..., description="A list of transitions")  # Transitions
    I: Inputs = Field(..., description="A list of inputs")  # Inputs
    O: Outputs = Field(..., description="A list of outputs")  # Outputs


@model_blueprint.post("/to_petrinet", response_model=PetriNetResponse, tags=["modeling"])
def model_to_petri(template_model: Dict[str, Any] = Body(..., example=template_model_example)):
    """Create a PetriNet model from a TemplateModel"""
    tm = TemplateModel.from_json(template_model)
    model = Model(tm)
    petri_net = PetriNetModel(model)
    petri_net_json = petri_net.to_json()
    return petri_net_json


# From PetriNetJson
@model_blueprint.post("/from_petrinet", tags=["modeling"], response_model=TemplateModel)
def petri_to_model(petri_json: Dict[str, Any] = Body(..., example=petrinet_json)):
    """Create a TemplateModel from a PetriNet model"""
    return template_model_from_petri_json(petri_json)


# Model stratification
class StratificationQuery(BaseModel):
    template_model: Dict[str, Any] = Field(
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
    tm = TemplateModel.from_json(stratification_query.template_model)
    template_model = stratify(
        template_model=tm,
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
    simplify: bool = Query(
        default=True,
        description="Whether to simplify the rate laws of the model.",
        example=True,
    ),
    aggregate_params: bool = Query(
        default=False,
        description="Whether to aggregate parameters of the model by creating"
                    "a new parameter to make rate laws more mass action like"
                    "if the actual rate law uses some function of constants"
                    "and one or more parameters.",
        example=False,
    )
):
    """Get a BioModels base template model by providing its model id"""
    try:
        xml_string = get_sbml_model(model_id=model_id)
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Bad model id")
    tm = template_model_from_sbml_string(xml_string, model_id=model_id)
    if simplify:
        tm = simplify_rate_laws(tm)
    if aggregate_params:
        tm = aggregate_parameters(tm)
    return tm


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
    template_model: Dict[str, Any] = Body(
        ...,
        description="A template model to turn into a bilayer json",
        example=template_model_example,
    )
):
    """Turn template model into a bilayer json"""
    # todo: Use model for bilayer to be used from above as response model
    tm = TemplateModel.from_json(template_model)
    bilayer_model = BilayerModel(Model(tm))
    return bilayer_model.bilayer


class XmlString(BaseModel):
    xml_string: str = Field(..., description="An SBML model as an XML string")


@model_blueprint.post("/sbml_xml_to_model", response_model=TemplateModel, tags=["modeling"])
def sbml_xml_to_model(
    xml: XmlString = Body(..., description="An XML string to turn into a template model")
):
    """Turn SBML XML into a template model"""
    tm = template_model_from_sbml_string(xml.xml_string)
    return tm


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
    template_model: Dict[str, Any] = Body(..., example=template_model_example),
):
    """Create a graphviz dot file from a TemplateModel"""
    tm = TemplateModel.from_json(template_model)
    return _graph_model(
        template_model=tm,
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
    template_model: Dict[str, Any] = Body(..., example=template_model_example),
):
    """Create a graph image from a TemplateModel"""
    tm = TemplateModel.from_json(template_model)
    return _graph_model(
        template_model=tm,
        file_suffix="png",
        file_format="png",
        media_type="image/png",
        background_tasks=bg_task,
    )


class TemplateModelDeltaQuery(BaseModel):
    template_model1: Dict[str, Any] = Field(..., example=template_model_example)
    template_model2: Dict[str, Any] = Field(
        ..., example=template_model_example_w_context
    )


def _generate_template_model_delta(
    request: Request,
    template_model1: TemplateModel,
    template_model2: TemplateModel,
) -> TemplateModelDelta:
    def _is_ontological_child(child_curie: str, parent_curie: str) -> bool:
        res = request.app.state.client.query_relations(
            source_curie=child_curie,
            relation_type=DKG_REFINER_RELS,
            target_curie=parent_curie,
        )
        # res is a list of lists, so check that there is at least one
        # element in the outer list and that the first element/list contains
        # something
        return len(res) > 0 and len(res[0]) > 0
    tmd = TemplateModelDelta(
        template_model1=template_model1,
        template_model2=template_model2,
        refinement_function=_is_ontological_child,
    )
    return tmd


@model_blueprint.post(
    "/models_to_delta_graph", response_model=Dict[str, Any], tags=["modeling"]
)
def models_to_delta_graph(
    request: Request,
    template_models: TemplateModelDeltaQuery = Body(
        ..., description="Provide two models to compare to each other"
    ),
):
    """Get the graph representing the difference between two models"""
    # Create a local helper to check for ontological children
    tmd = _generate_template_model_delta(
        request,
        template_model1=TemplateModel.from_json(template_models.template_model1),
        template_model2=TemplateModel.from_json(template_models.template_model2),
    )
    json_graph = tmd.graph_as_json()
    return json_graph


@model_blueprint.post(
    "/models_to_delta_image",
    response_class=FileResponse,
    response_description="A successful response returns a png image of the delta "
    "between the provided models",
    tags=["modeling"],
)
def models_to_delta_image(
    request: Request,
    bg_task: BackgroundTasks,
    template_models: TemplateModelDeltaQuery = Body(
        ..., description="Provide two models to compare to each other"
    ),
):
    tmd = _generate_template_model_delta(
        request,
        template_model1=TemplateModel.from_json(template_models.template_model1),
        template_model2=TemplateModel.from_json(template_models.template_model2),
    )
    fpath = viz_temp.join(name=f"{uuid.uuid4()}.png")
    fpath_str = fpath.absolute().as_posix()

    try:
        tmd.draw_graph(fpath_str)
    except Exception as exc:
        raise exc
    finally:
        bg_task.add_task(_delete_after_response, fpath)

    return FileResponse(
        path=fpath_str, media_type="image/png", filename="graph_delta.png"
    )


class AddTranstitionQuery(BaseModel):
    template_model: Dict[str, Any] = Field(
        ..., description="The template model to add the transition to", example=template_model_example
    )
    subject_concept: Concept = Field(..., description="The subject concept")
    outcome_concept: Concept = Field(..., description="The outcome concept")
    parameter: Optional[Parameter] = Field(default=None, description="The parameter (optional)")


@model_blueprint.post("/add_transition", response_model=TemplateModel, tags=["modeling"])
def add_transition(
    add_transition_query: AddTranstitionQuery = Body(
        ...,
        example={
            "template_model": template_model_example,
            "subject_concept": "<Add concept example>",
            "object_concept": "<Add concept example>",
            "parameter": "<Add parameter example>",
        },
    )
):
    """Add a transition between two concepts in a template model"""
    tm = TemplateModel.from_json(add_transition_query.template_model)
    template_model = tm.add_transition(
        subject_concept=add_transition_query.subject_concept,
        outcome_concept=add_transition_query.outcome_concept,
        parameter=add_transition_query.parameter,
    )
    return template_model


class ModelComparisonQuery(BaseModel):
    template_models: List[Dict[str, Any]] = Field(
        ..., example=[
            template_model_example, template_model_example_w_context
        ]
    )


class ModelComparisonResponse(BaseModel):
    graph_comparison_data: ModelComparisonGraphdata
    similary_scores: List[Dict[str, Union[Tuple[int, int], float]]] = Field(
        ..., description="A dictionary of similarity scores between all the "
                         "provided models."
    )


@model_blueprint.post("/model_comparison",
                      response_model=ModelComparisonResponse,
                      tags=["modeling"])
def model_comparison(
        request: Request,
        query: ModelComparisonQuery
):
    """Compare a list of models to each other"""

    def _is_ontological_child(child_curie: str, parent_curie: str) -> bool:
        res = request.app.state.client.query_relations(
            source_curie=child_curie,
            relation_type=DKG_REFINER_RELS,
            target_curie=parent_curie,
        )
        # res is a list of lists, so check that there is at least one
        # element in the outer list and that the first element/list contains
        # something
        return len(res) > 0 and len(res[0]) > 0

    template_models = [TemplateModel.from_json(m) for m in query.template_models]
    graph_comparison_data = ModelComparisonGraphdata.from_template_models(
        template_models, refinement_func=_is_ontological_child
    )
    resp = ModelComparisonResponse(
        graph_comparison_data=graph_comparison_data,
        similarity_scores=graph_comparison_data.get_similarity_scores(),
    )
    breakpoint()
    return resp
