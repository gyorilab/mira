from mira.metamodel import *
from mira.sources.askenet import model_from_url
from mira.sources.askenet import petrinet
from mira.sources.askenet import regnet

petrinet_example = 'https://raw.githubusercontent.com/DARPA-ASKEM/' \
    'Model-Representations/main/petrinet/examples/sir.json'
regnet_example = 'https://raw.githubusercontent.com/DARPA-ASKEM/' \
    'Model-Representations/main/regnet/examples/lotka_volterra.json'


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