"""Client functionality to Terarium."""

from typing import Dict, List, Union

import requests
from pydantic import BaseModel

from mira.metamodel import TemplateModel
from mira.modeling import Model
from mira.modeling.amr.petrinet import AMRPetriNetModel
from mira.sources.amr import sanity_check_amr
from mira.sources.amr.petrinet import model_from_url

__all__ = [
    "associate",
    "post_template_model",
    "post_amr",
    "post_amr_remote",
    "get_template_model",
]


def associate(*, project_id: str, model_id: str) -> str:
    """Associate a model (UUID) to a project (UUID) and return the association UUID

    Parameters
    ----------
    project_id :
        UUID of the project
    model_id :
        UUID of the model

    Returns
    -------
    :
        UUID of the association
    """
    x = f"http://data-service.staging.terarium.ai/projects/{project_id}/assets/models/{model_id}"
    res = requests.post(x)
    return res.json()["id"]


class TerariumResponse(BaseModel):
    model_id: str
    associations: Dict[str, str]


def post_template_model(
    template_model: TemplateModel,
    project_id: Union[str, List[str], None] = None,
) -> TerariumResponse:
    """Post a template model to Terarium as a Petri Net AMR.

    Optionally add to a project(s) if given.

    Parameters
    ----------
    template_model :
        TemplateModel to post
    project_id :
        UUID of the project to add model to (optional)

    Returns
    -------
    :
        TerariumResponse
    """
    model = AMRPetriNetModel(Model(template_model))
    amr_json = model.to_json()
    sanity_check_amr(amr_json)
    return post_amr(amr_json, project_id=project_id)


def post_amr(
    amr, project_id: Union[str, List[str], None] = None
) -> TerariumResponse:
    """Post an AMR to Terarium.

    Optionally add to a project(s) if given.

    Parameters
    ----------
    amr :
        AMR to post
    project_id :
        UUID of the project to add model to (optional)

    Returns
    -------
    :
        TerariumResponse
    """
    res = requests.post(
        "http://data-service.staging.terarium.ai/models", json=amr
    )
    res_json = res.json()
    model_id = res_json["id"]
    associations: Dict[str, str] = {}
    if isinstance(project_id, str):
        associations[project_id] = associate(
            project_id=project_id, model_id=model_id
        )
    elif isinstance(project_id, list):
        for i in project_id:
            associations[i] = associate(project_id=i, model_id=model_id)
    return TerariumResponse(model_id=model_id, associations=associations)


def post_amr_remote(
    model_url: str, *, project_id: Union[str, List[str], None] = None
) -> TerariumResponse:
    """Download an AMR from a URL then post to Terarium.

    Optionally add to a project(s) if given.

    To add the July 2023 evaluation scenario 3 base model to the evaluation project,
    run the following:

    >>> post_amr_remote(
    >>>     "https://raw.githubusercontent.com/gyorilab/mira/hackathon/"
    >>>     "notebooks/evaluation_2023.07/eval_scenario3_base.json",
    >>>     project_id="37",
    >>> )

    Parameters
    ----------
    model_url :
        URL to download AMR from
    project_id :
        UUID of the project to add model to (optional)

    Returns
    -------
    :
        TerariumResponse
    """
    model_amr_json = requests.get(model_url).json()
    return post_amr(model_amr_json, project_id=project_id)


def get_template_model(model_id: str) -> TemplateModel:
    """Get a template model from Terarium by its model UUID

    Parameters
    ----------
    model_id :
        UUID of the model

    Returns
    -------
    :
        TemplateModel of the model
    """
    return model_from_url(f"http://data-service.staging.terarium.ai/models/{model_id}")
