"""Modeling blueprint

This submodule serves as an API for modeling
"""
import json
import uuid
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, List, Literal, Optional, Set, Type, Union

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

from mira.examples.sir import sir_bilayer, sir, sir_parameterized_init, sir_2_city
from mira.metamodel import (
    NaturalConversion, Template, ControlledConversion,
    stratify, Concept, ModelComparisonGraphdata, TemplateModelDelta,
    TemplateModel, Parameter, simplify_rate_laws, aggregate_parameters,
    counts_to_dimensionless
)
from mira.modeling import Model
from mira.modeling.amr.petrinet import AMRPetriNetModel, ModelSpecification
from mira.modeling.bilayer import BilayerModel
from mira.modeling.acsets.petri import PetriNetModel, PetriNetResponse
from mira.modeling.viz import GraphicalModel
from mira.sources.amr.flux_span import reproduce_ode_semantics, \
    test_file_path, docker_test_file_path
from mira.sources.amr.petrinet import template_model_from_amr_json
from mira.sources.bilayer import template_model_from_bilayer
from mira.sources.biomodels import get_sbml_model
from mira.sources.acsets.petri import template_model_from_petri_json
from mira.sources.sbml import template_model_from_sbml_string

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

#: PetriNetModel json example
petrinet_json = PetriNetModel(Model(sir)).to_pydantic()
amr_petrinet_json = AMRPetriNetModel(Model(sir)).to_pydantic()
amr_petrinet_json_2_city = AMRPetriNetModel(Model(sir_2_city)).to_pydantic()
amr_petrinet_json_units_values = AMRPetriNetModel(
    Model(sir_parameterized_init)
).to_pydantic()


@model_blueprint.post(
    "/to_petrinet_acsets",
    response_model=PetriNetResponse,
    tags=["modeling"],
    description=dedent("""\
        This endpoint consumes a JSON representation of a MIRA template model and converts
        it into the ACSet standard for petri nets (implicitly defined 
        [here](https://github.com/AlgebraicJulia/py-acsets/blob/main/src/acsets/petris.py)),
        which can be used with the Algebraic Julia ecosystem.
        
        Note, this endpoint used to be called "/api/to_petrinet" but has been renamed as the ASKEM
        standard now uses that endpoint.
    """.rstrip()),
)
def model_to_petri(template_model: Dict[str, Any] = Body(...,
                                                         examples=[
                                                             template_model_example])):
    """Create a PetriNet model from a TemplateModel"""
    tm = TemplateModel.from_json(template_model)
    model = Model(tm)
    petri_net = PetriNetModel(model)
    return petri_net.to_pydantic()


# From PetriNetJson
@model_blueprint.post(
    "/from_petrinet_acsets",
    tags=["modeling"],
    response_model=TemplateModel,
    description=dedent("""\
        This endpoint consumes a JSON representation of an
        [ACSet petri net](https://github.com/AlgebraicJulia/py-acsets/blob/main/src/acsets/petris.py)
        and produces a JSON representation of a MIRA template model, 
        which can be directly used with the MIRA ecosystem to do model
        extension, stratification, and comparison.

        Note, this endpoint used to be called "/api/from_petrinet" but has been renamed as the ASKEM
        standard now uses that endpoint.
    """.rstrip()),
)
def petri_to_model(petri_json: Dict[str, Any] = Body(...,
                                                     examples=[petrinet_json])):
    """Create a TemplateModel from a PetriNet model"""
    return template_model_from_petri_json(petri_json)


@model_blueprint.post(
    "/to_petrinet",
    response_model=ModelSpecification,
    tags=["modeling"],
    description=dedent("""\
        This endpoint consumes a JSON representation of a MIRA template model and converts
        it into the
        [ASKEM standard for petri nets](https://github.com/DARPA-ASKEM/Model-Representations/blob/main/petrinet/petrinet_schema.json),
        which can be directly consumed by other project members that 
        implement this standard.
    """.rstrip()),
)
def model_to_amr(template_model: Dict[str, Any] = Body(...,
                                                       examples=[template_model_example])):
    """Create an AMR Petri model from a TemplateModel."""
    tm = TemplateModel.from_json(template_model)
    model = Model(tm)
    amr_petrinet_model = AMRPetriNetModel(model)
    return amr_petrinet_model.to_pydantic()


@model_blueprint.post(
    "/from_petrinet",
    tags=["modeling"],
    response_model=TemplateModel,
    description=dedent("""\
        This endpoint consumes a JSON representation of an
        [ASKEM petri net](https://github.com/DARPA-ASKEM/Model-Representations/blob/main/petrinet/petrinet_schema.json)
        and produces a JSON representation of a MIRA template model, 
        which can be directly used with the MIRA ecosystem to do model 
        extension, stratification, and comparison.
    """.rstrip()),
)
def amr_to_model(amr_json: Dict[str, Any] = Body(...,
                                                 examples=[amr_petrinet_json])):
    """Create a TemplateModel from an AMR model."""
    return template_model_from_amr_json(amr_json)


# Model stratification
class StratificationQuery(BaseModel):
    template_model: Dict[str, Any] = Field(
        ...,
        description="The template model to stratify",
        examples=[template_model_example]
    )
    key: str = Field(
        ...,
        description="The (singular) name of the stratification",
        examples=["city"]
    )
    strata: Set[str] = Field(
        ...,
        description="A list of the values for stratification",
        examples=[["boston", "nyc"]]
    )
    strata_name_map: Union[Dict[str, str], None] = Field(
        None,
        description="A mapping of the strata values to names to be used in "
                    "renaming the concepts. If none given, will use the "
                    "strata values as the names. This option only has an "
                    "effect if ``modify_names`` is true.",
        examples=[{
            "geonames:4930956": "Boston", "geonames:5128581": "New York City"
        }],
    )
    strata_name_lookup: bool = Field(
        False,
        description="If true, will try to look up the entity names of the "
                    "strata values under the assumption that they are "
                    "curies. This flag has no impact if ``strata_name_map`` "
                    "is given.",
        examples=[True]
    )
    structure: Union[List[List[str]], None] = Field(
        None,
        description="An iterable of pairs corresponding to a directed network "
        "structure where each of the pairs has two strata. If none given, "
        "will assume a complete network structure.",
        examples=[[["boston", "nyc"]]],
    )
    directed: bool = Field(
        False,
        description="Whether the model has directed edges or not.",
        examples=[True]
    )
    conversion_cls: Literal["natural_conversion",
                            "controlled_conversion"] = Field(
        "natural_conversion",
        description="The template class to be used for conversions between "
                    "strata defined by the network structure.",
        examples=["natural_conversion"],
    )
    cartesian_control: bool = Field(
        False,
        description=dedent("""
        If true, splits all control relationships based on the stratification.

        This should be true for an SIR epidemiology model, the susceptibility to
        infected transition is controlled by infected. If the model is stratified by
        vaccinated and unvaccinated, then the transition from vaccinated
        susceptible population to vaccinated infected populations should be
        controlled by both infected vaccinated and infected unvaccinated
        populations.

        This should be false for stratification of an SIR epidemiology model based
        on cities, since the infected population in one city won't (directly,
        through the perspective of the model) affect the infection of susceptible
        population in another city.
        """),
        examples=[True]
    )
    modify_names: bool = Field(
        True,
        description="If true, will modify the names of the concepts to "
                    "include the strata (e.g., ``'S'`` becomes "
                    "``'S_boston'``). If false, will keep the original names.",
        examples=[True]
    )
    params_to_stratify: Optional[List[str]] = Field(
        None,
        description="A list of parameters to stratify. If none given, "
                    "will stratify all parameters.",
        examples=[["beta"]]
    )
    params_to_preserve: Optional[List[str]] = Field(
        None,
        description="A list of parameters to preserve. If none given, "
                    "will stratify all parameters.",
        examples=[["gamma"]]
    )
    concepts_to_stratify: Optional[List[str]] = Field(
        None,
        description="A list of concepts to stratify. If none given, "
                    "will stratify all concepts.",
        examples=[["susceptible", "infected"]],
    )
    concepts_to_preserve: Optional[List[str]] = Field(
        None,
        description="A list of concepts to preserve. If none given, "
                    "will stratify all concepts.",
        examples=[["recovered"]],
    )
    param_renaming_uses_strata_names: Optional[bool] = Field(
        False,
        description="If true, the strata names will be used in the parameter "
                    "renaming. If false, the strata indices will be used. "
                    "Default: False",
        examples=[False]
    )

    def get_conversion_cls(self) -> Type[Template]:
        if self.conversion_cls == "natural_conversion":
            return NaturalConversion
        return ControlledConversion


@model_blueprint.post("/stratify", response_model=TemplateModel, tags=["modeling"])
def model_stratification(
    request: Request,
    stratification_query: StratificationQuery = Body(
        ...,
        examples=[{
            "template_model": template_model_example,
            "key": "city",
            "strata": ["geonames:4930956", "geonames:5128581"],
            "strata_name_lookup": True,
            "params_to_stratify": ["beta"],
        }],
    )
):
    """Stratify a model according to the specified stratification"""
    strata = stratification_query.strata
    tm = TemplateModel.from_json(stratification_query.template_model)

    if (stratification_query.strata_name_map is None and
            stratification_query.strata_name_lookup):
        strata_name_map = {}
        for sn in strata:
            if ":" in sn:
                res = request.app.state.client.get_entity(sn)
                mapped_name = res.name if res is not None else sn
            else:
                mapped_name = sn
            strata_name_map[sn] = mapped_name
    elif stratification_query.strata_name_map:
        strata_name_map = stratification_query.strata_name_map
    else:
        strata_name_map = None

    template_model = stratify(
        template_model=tm,
        key=stratification_query.key,
        strata=strata,
        strata_curie_to_name=strata_name_map,
        structure=stratification_query.structure,
        directed=stratification_query.directed,
        conversion_cls=stratification_query.get_conversion_cls(),
        cartesian_control=stratification_query.cartesian_control,
        modify_names=stratification_query.modify_names,
        params_to_stratify=stratification_query.params_to_stratify,
        params_to_preserve=stratification_query.params_to_preserve,
        concepts_to_stratify=stratification_query.concepts_to_stratify,
        concepts_to_preserve=stratification_query.concepts_to_preserve,
        param_renaming_uses_strata_names=stratification_query.param_renaming_uses_strata_names
    )
    return template_model


@model_blueprint.post(
    "/counts_to_dimensionless_mira",
    response_model=TemplateModel,
    tags=["modeling"]
)
def dimension_transform(
        query: Dict[str, Any] = Body(
            ...,
            examples=[{
                "model": sir_parameterized_init,
                "counts_unit": "person",
                "norm_factor": 1e5,
            }],
        )
):
    """Convert all entity concentrations to dimensionless units"""
    # convert to template model
    tm_json = query.pop("model")
    tm = TemplateModel.from_json(tm_json)
    # The concepts should have their units' expressions as sympy.Expr,
    # currently they are strings
    tm_dimless = counts_to_dimensionless(tm=tm, **query)
    return tm_dimless


@model_blueprint.post(
    "/counts_to_dimensionless_amr",
    response_model=ModelSpecification,
    tags=["modeling"]
)
def dimension_transform(
        query: Dict[str, Any] = Body(
            ...,
            examples=[{
                "model": amr_petrinet_json_units_values,
                "counts_units": "persons",
                "norm_factor": 1e5,
            }],
        )
):
    """Convert all entity concentrations to dimensionless units"""
    # convert to template model
    amr_json = query.pop("model")
    tm = template_model_from_amr_json(amr_json)

    # Create a dimensionless model
    dimless_model = counts_to_dimensionless(tm=tm, **query)

    # Transform back to amr model
    return AMRPetriNetModel(Model(dimless_model)).to_pydantic()


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
        examples=["BIOMD0000000956"],
    ),
    simplify: bool = Query(
        default=True,
        description="Whether to simplify the rate laws of the model.",
        examples=[True],
    ),
    aggregate_params: bool = Query(
        default=False,
        description="Whether to aggregate parameters of the model by creating"
                    "a new parameter to make rate laws more mass action like"
                    "if the actual rate law uses some function of constants"
                    "and one or more parameters.",
        examples=[False],
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
        examples=[sir_bilayer],
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
        examples=[template_model_example],
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
    template_model: Dict[str, Any] = Body(..., examples=[
        template_model_example]),
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
    template_model: Dict[str, Any] = Body(..., examples=[
        template_model_example]),
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
    template_model1: Dict[str, Any] = Field(..., examples=[template_model_example])
    template_model2: Dict[str, Any] = Field(
        ..., examples=[template_model_example_w_context]
    )


def _generate_template_model_delta(
    request: Request,
    template_model1: TemplateModel,
    template_model2: TemplateModel,
) -> TemplateModelDelta:
    tmd = TemplateModelDelta(
        template_model1=template_model1,
        template_model2=template_model2,
        refinement_function=request.app.state.refinement_closure.is_ontological_child,
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
        ..., description="The template model to add the transition to", examples=[template_model_example]
    )
    subject_concept: Concept = Field(..., description="The subject concept")
    outcome_concept: Concept = Field(..., description="The outcome concept")
    parameter: Optional[Parameter] = Field(default=None, description="The parameter (optional)")


@model_blueprint.post("/add_transition", response_model=TemplateModel, tags=["modeling"])
def add_transition(
    add_transition_query: AddTranstitionQuery = Body(
        ...,
        examples=[{
            "template_model": template_model_example,
            "subject_concept": {"name": "infected population",
                                "identifiers": {"ido": "0000511"}},
            "outcome_concept": {"name": "dead",
                                "identifiers": {"ncit": "C28554"}},
        }],
    )
):
    """Add a transition between two concepts in a template model"""
    tm = TemplateModel.from_json(add_transition_query.template_model)
    template_model = tm.add_transition(
        subject_concept=add_transition_query.subject_concept,
        outcome_concept=add_transition_query.outcome_concept,
        mass_action_parameter=add_transition_query.parameter,
    )
    return template_model


class ModelComparisonQuery(BaseModel):
    template_models: List[Dict[str, Any]] = Field(
        ..., examples=[[
            template_model_example, template_model_example_w_context
        ]]
    )


class ModelComparisonResponse(BaseModel):
    graph_comparison_data: Union[Dict[str, Any], ModelComparisonGraphdata] #ModelComparisonGraphdata
    similarity_scores: List[Dict[str, Union[List[int], float]]] = Field(
        ..., description="A dictionary of similarity scores between all the "
                         "provided models."
    )


@model_blueprint.post("/model_comparison",
                      response_model=ModelComparisonResponse,
                      tags=["modeling"],
                      description="This endpoint consumes a list of "
                                  "template model JSON objects and returns "
                                  "similarity scores and the data comparing "
                                  "the models")
def model_comparison(
        request: Request,
        query: ModelComparisonQuery
):
    """Compare a list of models to each other"""
    template_models = [TemplateModel.from_json(m) for m in query.template_models]
    graph_comparison_data = ModelComparisonGraphdata.from_template_models(
        template_models, refinement_func=request.app.state.refinement_closure.is_ontological_child
    )
    resp = ModelComparisonResponse(
        graph_comparison_data=graph_comparison_data.model_dump(),
        similarity_scores=graph_comparison_data.get_similarity_scores(),
    )
    return resp


class AMRComparisonQuery(BaseModel):
    petrinet_models: List[Dict[str, Any]] = Field(
        ..., examples=[[amr_petrinet_json, amr_petrinet_json_2_city]]
    )


@model_blueprint.post("/askenet_model_comparison",
                      response_model=ModelComparisonResponse,
                      tags=["modeling"],
                      description="This endpoint consumes a list of amr "
                                  "petrinet JSON objects and returns "
                                  "similarity scores and the data comparing "
                                  "the models")
def askepetrinet_model_comparison(
        request: Request,
        query: AMRComparisonQuery
):
    """Compare a list of models to each other"""
    template_models = [
        template_model_from_amr_json(m) for m in query.petrinet_models
    ]
    graph_comparison_data = ModelComparisonGraphdata.from_template_models(
        template_models,
        refinement_func=request.
            app.state.refinement_closure.is_ontological_child
    )
    resp = ModelComparisonResponse(
        graph_comparison_data=graph_comparison_data.model_dump(),
        similarity_scores=graph_comparison_data.get_similarity_scores(),
    )
    return resp


if docker_test_file_path.exists():
    flux_span_query_example = json.loads(docker_test_file_path.read_text())
elif test_file_path.exists():
    flux_span_query_example = json.loads(test_file_path.read_text())
else:
    flux_span_query_example = None


class FluxSpanQuery(BaseModel):
    model: Dict[str, Any] = Field(
        ...,
        examples=[flux_span_query_example],
        description="The model to recover the ODE-semantics from.",
    )


@model_blueprint.post("/reconstruct_ode_semantics",
                      response_model=ModelSpecification,
                      tags=["modeling"])
def reproduce_ode_semantics_endpoint(
        query: FluxSpanQuery = Body(
            ...,
            description="Reproduce ODE semantics from a stratified model"
                        "(flux span)."
        )
):
    """Reproduce ODE semantics from a stratified model (flux span)."""
    tm = reproduce_ode_semantics(query.model)
    am = AMRPetriNetModel(Model(tm))
    return am.to_pydantic()
