__all__ = ['model_from_url', 'model_from_json_file']

import json
import requests
import mira.sources.askenet.petrinet as petrinet
import mira.sources.askenet.regnet as regnet


def model_from_url(url):
    """Return a model from a URL, handling multiple frameworks.

    Parameters
    ----------
    url :
        The URL to the JSON file.

    Returns
    -------
    :
        A TemplateModel object.
    """
    res = requests.get(url)
    model_json = res.json()
    if 'schema' not in model_json:
        raise ValueError(f'No "schema" defined in the AMR at {url}. '
                         f'The schema has to be a URL pointing to a '
                         f'JSON schema against which the AMR is validated.')
    if 'petrinet' in model_json['schema']:
        return petrinet.template_model_from_askenet_json(model_json)
    elif 'regnet' in model_json['schema']:
        return regnet.template_model_from_askenet_json(model_json)
    else:
        raise ValueError(f'Unknown schema: {model_json["schema"]}')


def model_from_json_file(fname):
    """Return a model from a file, handling multiple frameworks.

    Parameters
    ----------
    fname :
        The path to the JSON file.

    Returns
    -------
    :
        A TemplateModel object.
    """
    with open(fname) as fh:
        model_json = json.load(fh)
    if 'schema' not in model_json:
        raise ValueError(f'No schema defined in the AMR in {fname}. '
                         f'The schema has to be a URL pointing to a '
                         f'JSON schema against which the AMR is validated.')
    if 'petrinet' in model_json['schema']:
        return petrinet.template_model_from_askenet_json(model_json)
    elif 'regnet' in model_json['schema']:
        return regnet.template_model_from_askenet_json(model_json)
    else:
        raise ValueError(f'Unknown schema: {model_json["schema"]}')
