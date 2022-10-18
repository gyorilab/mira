from mira.examples.sir import sir
from mira.modeling import Model
from mira.modeling.petri import PetriNetModel


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
        assert transition['template_type'] in {'ControlledConversion',
                                               'NaturalConversion'}
