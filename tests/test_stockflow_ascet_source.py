from copy import deepcopy as _d
from mira.sources.askenet.stockflow_ascet import *
import requests


def set_up_file():
    return requests.get(
        'https://raw.githubusercontent.com/AlgebraicJulia/'
        'py-acsets/jpfairbanks-patch-1/src/acsets/schemas/examples/StockFlowp.json').json()


def test_stock_to_concept():
    stock = {
        "_id": 1,
        "sname": "S"
    }
    concept = stock_to_concept(stock)
    assert concept.name == str(stock['_id'])
    assert concept.display_name == stock['sname']


def test_flow_to_template():
    sf_ascet = _d(set_up_file())
    tm = template_model_from_sf_json(sf_ascet)

    assert len(tm.templates) == 2
    assert isinstance(tm.templates[0], ControlledConversion)
    assert isinstance(tm.templates[1], NaturalConversion)
    assert tm.templates[0].name == str(sf_ascet['Flow'][0]['_id'])
    assert tm.templates[1].name == str(sf_ascet['Flow'][1]['_id'])
    assert tm.templates[0].subject.name == str(sf_ascet['Flow'][0]['u'])
    assert tm.templates[0].outcome.name == str(sf_ascet['Flow'][0]['d'])
    assert tm.templates[0].controller.name == str(sf_ascet['Flow'][0]['d'])
    assert tm.templates[1].subject.name == str(sf_ascet['Flow'][1]['u'])
    assert tm.templates[1].outcome.name == str(sf_ascet['Flow'][1]['d'])
