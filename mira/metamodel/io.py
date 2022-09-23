import json
from .templates import TemplateModel


def model_from_json_file(fname):
    """Return a TemplateModel from a JSON file.

    Parameters
    ----------
    fname : str or Path
        A file path.

    Returns
    -------
    TemplateModel
        A TemplateModel deserialized from the JSON file.
    """
    with open(fname, 'r') as fh:
        return TemplateModel.from_json(json.load(fh))
