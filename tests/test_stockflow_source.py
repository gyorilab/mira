from copy import deepcopy as _d
import requests

from mira.metamodel import *
from mira.sources.askenet.stockflow import *


def set_up_file():
    return requests.get(
        'https://raw.githubusercontent.com/DARPA-ASKEM/Model-Representations'
        '/7f5e377225675259baa6486c64102f559edfd79f/stockflow/examples/sir.json').json()


def test_flow_to_template():
    sfamr = _d(set_up_file())
    tm = template_model_from_stockflow_amr_json(sfamr)
    assert len(tm.templates) == 2
    assert isinstance(tm.templates[0], ControlledConversion)
    assert isinstance(tm.templates[1], NaturalConversion)
    assert tm.templates[0].name == str(sfamr['model']['flows'][0]['id'])
    assert tm.templates[1].name == str(sfamr['model']['flows'][1]['id'])
    assert tm.templates[0].subject.name == str(sfamr['model']['flows'][0]['upstream_stock'])
    assert tm.templates[0].outcome.name == str(sfamr['model']['flows'][0]['downstream_stock'])
    assert tm.templates[0].controller.name == str(sfamr['model']['flows'][0]['downstream_stock'])
    assert tm.templates[1].subject.name == str(sfamr['model']['flows'][1]['upstream_stock'])
    assert tm.templates[1].outcome.name == str(sfamr['model']['flows'][1]['downstream_stock'])


def test_parameter_to_mira():
    sfamr = _d(set_up_file())
    tm = template_model_from_stockflow_amr_json(sfamr)
    for amr_param, tm_param in zip(sfamr['semantics']['ode']['parameters'], tm.parameters.values()):
        assert amr_param['id'] == tm_param.name
        assert amr_param['name'] == tm_param.display_name
        assert amr_param['description'] == tm_param.description
        assert amr_param['value'] == tm_param.value
        assert amr_param.get('units', {}) == (tm_param.units if tm_param.units else {})


def test_initial_to_mira():
    sfamr = _d(set_up_file())
    tm = template_model_from_stockflow_amr_json(sfamr)
    for amr_initial, tm_initial in zip(sfamr['semantics']['ode']['initials'], tm.initials.values()):
        assert amr_initial['target'] == tm_initial.concept.name
        assert amr_initial['expression'] == str(tm_initial.expression)
        assert amr_initial['expression_mathml'] == expression_to_mathml(tm_initial.expression)


def test_stock_to_concept():
    stock = {
        "id": "S",
        "name": "Susceptible",
        "grounding": {
            "identifiers": {
                "ido": "0000514"
            },
            "modifiers":{
                "test_key": "test_value"
            }
        }
    }

    concept = stock_to_concept(stock)
    assert concept.name == str(stock['id'])
    assert concept.display_name == stock['name']
    assert concept.context == stock['grounding']['modifiers']
    assert concept.identifiers == stock['grounding']['identifiers']
