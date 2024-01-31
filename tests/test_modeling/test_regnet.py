from mira.sources import amr
from mira.modeling import Model
from mira.metamodel.ops import stratify

from mira.modeling.amr.petrinet import template_model_to_petrinet_json
from mira.modeling.amr.regnet import AMRRegNetModel


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
    AMRRegNetModel(Model(model)).to_json()
    AMRRegNetModel(Model(model_2_city)).to_json()
