from copy import deepcopy

from mira.metamodel import Distribution
from mira.examples.sir import sir, sir_parameterized
from mira.modeling import Model
from mira.modeling.acset.petri import PetriNetModel


def test_petri_net_assembly():
    model = Model(sir)
    petri_net = PetriNetModel(model)
    js = petri_net.to_json()
    assert set(js) == {'S', 'T', 'I', 'O'}
    assert len(js['T']) == 2
    assert len(js['S']) == 3
    assert len(js['I']) == 3
    assert len(js['O']) == 3

    for entry in [{"ot": 1, "os": 2},
                  {"ot": 1, "os": 2},
                  {"ot": 2, "os": 3}]:
        assert entry in js['O']

    for entry in [{"it": 1, "is": 1},
                  {"it": 1, "is": 2},
                  {"it": 2, "is": 2}]:
        assert entry in js['I']

    transition_keys = {d['tname'] for d in js['T']}
    assert {f't{ix+1}' for ix in range(len(js['T']))} == transition_keys
    for transition in js['T']:
        assert transition['tprop']['template_type'] in {'ControlledConversion',
                                                        'NaturalConversion'}


def test_petri_parameterized():
    template_model = deepcopy(sir_parameterized)
    distr = Distribution(type='LogNormal1',
                         parameters={'meanLog': 0.1,
                                     'stdevLog': 0.2})
    template_model.parameters['beta'].distribution = distr
    model = Model(template_model)
    petri_net = PetriNetModel(model)
    js = petri_net.to_json()
    assert js
    assert js['S'][0]['concentration'] == 1
    assert js['T'][0]['rate'] == 0.1
    assert js['T'][0]['tprop']['parameter_distribution'] == distr.json()
