__all__ = ['model_from_url', 'model_from_json_file', 'model_from_json', 'sanity_check_amr']

import json

import jsonschema
import requests
import mira.sources.amr.petrinet as petrinet
import mira.sources.amr.regnet as regnet
import mira.sources.amr.stockflow as stockflow


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
    return model_from_json(model_json)


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
    return model_from_json(model_json)


def model_from_json(model_json):
    """Return a model from a JSON object, handling multiple frameworks.

    Parameters
    ----------
    model_json :
        The JSON object containing the model information.

    Returns
    -------
    :
        A TemplateModel object.
    """
    header = model_json.get('header', {})
    if 'schema' not in header:
        raise ValueError(f'No schema defined in the AMR in {fname}. '
                         f'The schema has to be a URL pointing to a '
                         f'JSON schema against which the AMR is validated.')
    if 'petrinet' in header['schema']:
        return petrinet.template_model_from_amr_json(model_json)
    elif 'regnet' in header['schema']:
        return regnet.template_model_from_amr_json(model_json)
    elif 'stockflow' in header['schema']:
        return stockflow.template_model_from_amr_json(model_json)
    else:
        raise ValueError(f'Unknown schema: {header["schema"]}')
    

def sanity_check_amr(amr_json):
    assert 'header' in amr_json
    assert 'schema' in amr_json['header']
    schema_json = requests.get(amr_json['header']['schema']).json()
    jsonschema.validate(schema_json, amr_json)
