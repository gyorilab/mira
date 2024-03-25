from mira.sources import amr
from mira.modeling import Model
from mira.metamodel import *

from mira.modeling.amr.regnet import AMRRegNetModel, \
    template_model_to_regnet_json
from mira.sources.amr.regnet import template_model_from_amr_json

def test_regnet_end_to_end():
    url = 'https://raw.githubusercontent.com/DARPA-ASKEM/' \
          'Model-Representations/main/regnet/examples/lotka_volterra.json'

    model = amr.regnet.model_from_url(url)

    model_2_city = stratify(
        model,
        key="city",
        strata=[
            "Toronto",
            "Montreal",
        ],
    )

    # Smoke tests to make sure exports work
    ex1 = AMRRegNetModel(Model(model)).to_json()
    ex2 = AMRRegNetModel(Model(model_2_city)).to_json()
    assert ex1 == template_model_to_regnet_json(model)
    assert ex2 == template_model_to_regnet_json(model_2_city)


def test_regnet_from_control():
    x = Concept(name='x')
    y = Concept(name='y')
    # We test in both directions to make sure the order of the controllers
    # doesn't matter
    t1 = GroupedControlledProduction(controllers=[x, y], outcome=x)
    t2 = GroupedControlledProduction(controllers=[y, x], outcome=x)

    for t in [t1, t2]:
        tm = TemplateModel(templates=[t1])
        reg = template_model_to_regnet_json(tm)

        edge = reg['model']['edges'][0]
        assert edge['id'] == 't1'
        assert edge['source'] == 'y'
        assert edge['target'] == 'x'
        assert edge['sign'] is True


def test_custom_rates():
    import numpy
    import sympy
    import matplotlib.pyplot as plt

    from mira.modeling import Model
    from mira.modeling.viz import GraphicalModel
    from mira.modeling.ode import OdeModel, simulate_ode_model
    from mira.modeling.amr.regnet import template_model_to_regnet_json
    from mira.modeling.amr.petrinet import template_model_to_petrinet_json

    p = lambda: Concept(name='p')  # protein
    r = lambda: Concept(name='r')  # rna

    t2 = NaturalDegradation(subject=r())
    t2.set_mass_action_rate_law('V')
    t3 = ControlledProduction(controller=r(), outcome=p())
    t3.set_mass_action_rate_law('L')
    t4 = NaturalDegradation(subject=p())
    t4.set_mass_action_rate_law('U')

    params = {'V': Parameter(name='V', value=0.03),
              'L': Parameter(name='L', value=2),
              'U': Parameter(name='U', value=0.15)}

    initials = {
        'p': Initial(concept=p(), expression=sympy.Float(100)),
        'r': Initial(concept=r(), expression=sympy.Float(3))
    }

    tm = TemplateModel(
        templates=[t2, t3, t4],
        parameters=params,
        initials=initials
    )

    rj = template_model_to_regnet_json(tm)
    print(rj)
    r = [v for v in rj['model']['vertices'] if v['id'] == 'r'][0]
    assert r['initial'] == 3.0
    assert r['rate_constant'] == 'V'
    assert r['sign'] is False


def test_regnet_observable_roundtrip():
    import sympy
    t = NaturalDegradation(subject=Concept(name='x'))
    observable = Observable(name='x', expression=sympy.Symbol('x'))
    tm = TemplateModel(templates=[t], observables={'xo': observable})
    rj = template_model_to_regnet_json(tm)
    tm2 = template_model_from_amr_json(rj)
    assert tm2.observables
