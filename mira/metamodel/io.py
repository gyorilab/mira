__all__ = ["model_from_json_file", "model_to_json_file"]

import json
from .template_model import TemplateModel


def model_from_json_file(fname) -> TemplateModel:
    """Return a TemplateModel from a JSON file.

    Parameters
    ----------
    fname : str or Path
        A file path.

    Returns
    -------
    :
        A TemplateModel deserialized from the JSON file.
    """
    with open(fname, 'r') as fh:
        return TemplateModel.from_json(json.load(fh))


def model_to_json_file(model: TemplateModel, fname):
    """Dump a TemplateModel into a JSON file.

    Parameters
    ----------
    model : TemplateModel
        A template model to dump to a JSON file.
    fname : str or Path
        A file path to dump the model into.
    """
    with open(fname, 'w') as fh:
        json.dump(json.loads(model.json()), fh, indent=1)
