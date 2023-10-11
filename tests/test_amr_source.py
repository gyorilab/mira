import requests
from mira.metamodel import *
from mira.sources.amr import model_from_url
from mira.sources.amr import petrinet
from mira.sources.amr import regnet
from mira.sources.amr import stockflow

petrinet_example = 'https://raw.githubusercontent.com/DARPA-ASKEM/' \
    'Model-Representations/main/petrinet/examples/sir.json'
regnet_example = 'https://raw.githubusercontent.com/DARPA-ASKEM/' \
    'Model-Representations/main/regnet/examples/lotka_volterra.json'
stockflow_example = 'https://raw.githubusercontent.com/DARPA-ASKEM/' \
    'Model-Representations/7f5e377225675259baa6486c64102f559edfd79f/stockflow/examples/sir.json'


def stockflow_set_up_file():
    return requests.get(stockflow_example).json()


def test_petrinet_model_from_url():
    template_model = petrinet.model_from_url(petrinet_example)
    assert len(template_model.templates) == 2
    assert isinstance(template_model.templates[0], ControlledConversion)
    assert isinstance(template_model.templates[1], NaturalConversion)
    assert template_model.templates[0].controller.display_name == 'Infected'
    assert template_model.templates[0].controller.name == 'I'
    assert template_model.templates[0].subject.display_name == 'Susceptible'
    assert template_model.templates[0].outcome.display_name == 'Infected'
    assert template_model.templates[1].subject.display_name == 'Infected'
    assert template_model.templates[1].outcome.display_name == 'Recovered'


def test_regnet_model_from_url():
    template_model = regnet.model_from_url(regnet_example)
    assert len(template_model.templates) == 4
    assert isinstance(template_model.templates[0], ControlledProduction)
    assert isinstance(template_model.templates[1], NaturalDegradation)
    assert isinstance(template_model.templates[2], ControlledDegradation)
    assert isinstance(template_model.templates[3], GroupedControlledProduction)


def test_model_from_url_generic():
    tm = model_from_url(regnet_example)
    assert len(tm.templates) == 4

    tm = model_from_url(petrinet_example)
    assert len(tm.templates) == 2


def test_stockflow_flow_to_template():
    tm = stockflow.model_from_url(stockflow_example)
    assert len(tm.templates) == 2
    assert isinstance(tm.templates[0], ControlledConversion)
    assert isinstance(tm.templates[1], NaturalConversion)
    assert tm.templates[0].name == 'flow1'
    assert tm.templates[1].name == 'flow2'
    assert tm.templates[0].subject.name == 'S'
    assert tm.templates[0].outcome.name == 'I'
    assert tm.templates[0].controller.name == 'I'
    assert tm.templates[1].subject.name == 'I'
    assert tm.templates[1].outcome.name == 'R'


def test_stockflow_parameter_to_mira():
    sfamr = stockflow_set_up_file()
    tm = stockflow.model_from_url(stockflow_example)
    for amr_param, tm_param in zip(sfamr['semantics']['ode']['parameters'], tm.parameters.values()):
        assert amr_param['id'] == tm_param.name
        assert amr_param['name'] == tm_param.display_name
        assert amr_param['description'] == tm_param.description
        assert amr_param['value'] == tm_param.value
        assert amr_param.get('units', {}) == (tm_param.units if tm_param.units else {})


def test_stockflow_initial_to_mira():
    sfamr = stockflow_set_up_file()
    tm = stockflow.model_from_url(stockflow_example)
    for amr_initial, tm_initial in zip(sfamr['semantics']['ode']['initials'], tm.initials.values()):
        assert amr_initial['target'] == tm_initial.concept.name
        assert amr_initial['expression'] == str(tm_initial.expression)
        assert amr_initial['expression_mathml'] == expression_to_mathml(tm_initial.expression)


def test_stockflow_stock_to_concept():
    stock = {
        "id": "S",
        "name": "Susceptible",
        "grounding": {
            "identifiers": {
                "ido": "0000514"
            },
            "modifiers": {
                "test_key": "test_value"
            }
        }
    }

    concept = stockflow.stock_to_concept(stock)
    assert concept.name == str(stock['id'])
    assert concept.display_name == stock['name']
    assert concept.context == stock['grounding']['modifiers']
    assert concept.identifiers == stock['grounding']['identifiers']
