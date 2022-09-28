from mira.metamodel import *
from mira.modeling import Model


def test_degradation_production():
    template = NaturalDegradation(subject=Concept(name='x'))
    tmodel = TemplateModel(templates=[template])
    model = Model(tmodel)
    assert len(model.variables) == 1

    template2 = NaturalProduction(outcome=Concept(name='x'))
    tmodel = TemplateModel(templates=[template, template2])
    model = Model(tmodel)
    assert len(model.variables) == 1
