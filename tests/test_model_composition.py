from mira.metamodel.composition import *
from mira.sources.amr import model_from_url
from mira.examples.sir import sir, sir_2_city


def test_model_compose():
    sir_petrinet_url = 'https://raw.githubusercontent.com/DARPA-ASKEM/' \
                       'Model-Representations/main/petrinet/examples/sir.json'
    lotka_regnet_url = ('https://raw.githubusercontent.com/DARPA-ASKEM'
                        '/Model-Representations/main/regnet'
                        '/examples/lotka_volterra.json')

    tm0 = model_from_url(sir_petrinet_url)
    tm1 = model_from_url(lotka_regnet_url)

    new_tm = compose([tm0, tm1, sir, sir_2_city])

