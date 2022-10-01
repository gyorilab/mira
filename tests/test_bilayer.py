from mira.metamodel import ControlledConversion, NaturalConversion
from mira.sources.bilayer import template_model_from_bilayer


sir_bilayer = \
    {"Wa": [{"influx": 1, "infusion": 2},
            {"influx": 2, "infusion": 3}],
     "Win": [{"arg": 1, "call": 1},
             {"arg": 2, "call": 1},
             {"arg": 2, "call": 2}],
     "Box": [{"parameter": "beta"},
             {"parameter": "gamma"}],
     "Qin": [{"variable": "S"},
             {"variable": "I"},
             {"variable": "R"}],
     "Qout": [{"tanvar": "S'"},
              {"tanvar": "I'"},
              {"tanvar": "R'"}],
     "Wn": [{"efflux": 1, "effusion": 1},
            {"efflux": 2, "effusion": 2}]}


def test_process_bilayer():
    tmodel = template_model_from_bilayer(sir_bilayer)
    templates = tmodel.templates
    assert len(templates) == 2
    cc = templates[0]
    assert isinstance(cc, ControlledConversion)
    assert cc.controller.name == 'I'
    assert cc.subject.name == 'S'
    assert cc.outcome.name == 'I'
    nc = templates[1]
    assert isinstance(nc, NaturalConversion)
    assert nc.subject.name == 'I'
    assert nc.outcome.name == 'R'
