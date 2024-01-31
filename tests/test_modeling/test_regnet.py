from mira.sources import amr
from mira.modeling import Model
from mira.metamodel.ops import stratify

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