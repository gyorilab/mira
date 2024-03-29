from sympy import Symbol
from mira.examples.sir import sir_bilayer
from mira.metamodel import Concept, ControlledConversion, NaturalConversion
from mira.metamodel.template_model import TemplateModel, Parameter
from mira.modeling import Model
from mira.modeling.bilayer import BilayerModel
from mira.sources.bilayer import template_model_from_bilayer


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


def test_generate_bilayer():
    S = Concept(name='S')
    I = Concept(name='I')
    R = Concept(name='R')
    templates = [
        ControlledConversion(subject=S, outcome=I, controller=I,
                             rate_law=Symbol('beta')*Symbol('S')*Symbol('I')),
        NaturalConversion(subject=I,  outcome=R,
                          rate_law=Symbol('gamma')*Symbol('I'))
    ]
    tm = TemplateModel(templates=templates,
                       parameters={'beta': Parameter(name='beta', value=1),
                                   'gamma': Parameter(name='gamma', value=1)})

    model = Model(template_model=tm)
    bm = BilayerModel(model)
    # These should be exactly the same as the example above
    equal_keys = ['Wa', 'Win', 'Wn', 'Qin', 'Qout']
    for key in equal_keys:
        assert sorted(bm.bilayer[key], key=lambda x: str(x)) == \
            sorted(sir_bilayer[key], key=lambda x: str(x))

    assert len(sir_bilayer['Box']) == len(bm.bilayer['Box'])
    assert all(set(box) == {'parameter'} and isinstance(box['parameter'], str)
               for box in bm.bilayer['Box'])
    assert bm.bilayer['Box'][0]['parameter'] == 'beta'
    assert bm.bilayer['Box'][1]['parameter'] == 'gamma'
