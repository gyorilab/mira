from mira.sources import amr
from mira.modeling import Model
from mira.metamodel import *

from mira.modeling.amr.regnet import AMRRegNetModel, \
    template_model_to_regnet_json


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
    t1 = GroupedControlledProduction(controllers=[x, y], outcome=x)
    t2 = GroupedControlledProduction(controllers=[y, x], outcome=x)
    tm = TemplateModel(templates=[t1])
    reg = template_model_to_regnet_json(tm)

    edge = reg['model']['edges'][0]
    assert edge['id'] == 't1'
    assert edge['source'] == 'y'
    assert edge['target'] == 'x'
    assert edge['sign'] is True
