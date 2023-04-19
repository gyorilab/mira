from mira.examples.sir import sir_parameterized
from mira.metamodel import *
from mira.modeling import Model
from mira.modeling.askenet.petrinet import AskeNetPetriNetModel
from mira.sources.askenet.petrinet import (
    model_from_url,
    template_model_from_askenet_json,
)

example = ('https://raw.githubusercontent.com/DARPA-ASKEM/'
           'Model-Representations/main/petrinet/examples/sir.json')


def test_model_from_url():
    template_model = model_from_url(example)
    assert len(template_model.templates) == 2
    assert isinstance(template_model.templates[0], ControlledConversion)
    assert isinstance(template_model.templates[1], NaturalConversion)
    assert template_model.templates[0].controller.name == 'Infected'
    assert template_model.templates[0].subject.name == 'Susceptible'
    assert template_model.templates[0].outcome.name == 'Infected'
    assert template_model.templates[1].subject.name == 'Infected'
    assert template_model.templates[1].outcome.name == 'Recovered'


def test_export():
    pm = AskeNetPetriNetModel(Model(sir_parameterized))
    pm.to_pydantic()
    model_json = pm.to_json()
    new_template_model = template_model_from_askenet_json(model_json)
    assert sir_parameterized == new_template_model
