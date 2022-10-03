from mira.examples.sir import sir_bilayer
from mira.metamodel import Concept, ControlledConversion, NaturalConversion, \
    TemplateModel
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
    templates = [ControlledConversion(subject=S, outcome=I, controller=I),
                 NaturalConversion(subject=I,  outcome=R)]

    model = Model(template_model=TemplateModel(templates=templates))
    bm = BilayerModel(model)
    # These should be exactly the same as the example above
    equal_keys = ['Wa', 'Win', 'Wn', 'Qin', 'Qout']
    for key in equal_keys:
        assert sorted(bm.bilayer[key], key=lambda x: str(x)) == \
            sorted(sir_bilayer[key], key=lambda x: str(x))

    assert len(sir_bilayer['Box']) == len(bm.bilayer['Box'])
    assert all(set(box) == {'parameter'} and isinstance(box['parameter'], str)
               for box in bm.bilayer['Box'])
