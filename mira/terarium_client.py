"""Client functionality to Terarium."""

from typing import List, Union

import jsonschema
import requests

from metamodel import TemplateModel
from mira.modeling import Model
from mira.modeling.askenet.petrinet import AskeNetPetriNetModel

__all__ = [
    "associate",
    "post_template_model",
    "post_amr",
    "post_amr_remote",
]


def associate(*, project_id: str, model_id: str) -> str:
    """Associate a model (UUID) to a project (UUID) and return the association UUID."""
    x = f"http://data-service.staging.terarium.ai/projects/{project_id}/assets/models/{model_id}"
    res = requests.post(x)
    return res.json()["id"]


def sanity_check_amr(amr_json):
    assert "schema" in amr_json
    schema_json = requests.get(amr_json["schema"]).json()
    jsonschema.validate(schema_json, amr_json)


def post_template_model(
    template_model: TemplateModel,
    project_id: Union[str, List[str], None] = None,
):
    """Post a template model to Terarium as a Petri Net AMR."""
    am = AskeNetPetriNetModel(Model(template_model))
    sanity_check_amr(am.to_json())
    return post_amr(am.to_json(), project_id=project_id)


def post_amr(amr, project_id: Union[str, List[str], None] = None):
    """Post an AMR to terarium.

    Optionally add to a project(s) if given.
    """
    res = requests.post("http://data-service.staging.terarium.ai/models", json=amr)
    res_json = res.json()
    res_id = res_json["id"]
    associations = {}
    if isinstance(project_id, str):
        associations[project_id] = associate(project_id=project_id, model_id=res.json()["id"])
    elif isinstance(project_id, list):
        for i in project_id:
            associations[i] = associate(project_id=i, model_id=res.json()["id"])
    return {
        "id": res_id,
        "associations": associations,
    }


def post_amr_remote(model_url: str, *, project_id: Union[str, List[str], None] = None):
    """Download an AMR from a URL then post to terarium.

    Optionally add to a project(s) if given.
    """
    model_amr_json = requests.get(model_url).json()
    return post_amr(model_amr_json, project_id=project_id)


if __name__ == '__main__':
    print(post_amr_remote(
        "https://raw.githubusercontent.com/indralab/mira/hackathon/notebooks/evaluation_2023.07/eval_scenario3_base.json",
        project_id="37",
    ))
