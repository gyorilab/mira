import requests
from copy import deepcopy as _d
from mira.sources.amr.stockflow import *
from mira.modeling.amr.stockflow import *

stockflow_example = 'https://raw.githubusercontent.com/DARPA-ASKEM/' \
                    'Model-Representations/7f5e377225675259baa6486c64102f559edfd79f/stockflow/examples/sir.json'


def set_up_file():
    return requests.get(stockflow_example).json()


def test_stockflow_assembley():
    sfamr = _d(set_up_file())
    tm = template_model_from_stockflow_amr_json(sfamr)
    sfamr_output = template_model_to_stockflow_amr_json(tm)

    model = sfamr_output['model']
    semantics_ode = sfamr_output['semantics']['ode']

    flows = model['flows']
    stocks = model['stocks']
    auxiliaries = model['auxiliaries']
    links = model['links']
    parameters = semantics_ode['parameters']
    initials = semantics_ode['initials']

    assert flows[0]['id'] == 'flow1'
    assert flows[1]['id'] == 'flow2'
