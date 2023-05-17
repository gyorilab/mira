from mira.sources.askenet import model_from_url


def test_model_from_url():
    tm = model_from_url('https://raw.githubusercontent.com/DARPA-ASKEM/'
                        'Model-Representations/main/regnet/examples/'
                        'lotka_volterra.json')
    assert len(tm.templates) == 4

    tm = model_from_url('https://raw.githubusercontent.com/DARPA-ASKEM/'
                        'Model-Representations/main/petrinet/examples/'
                        'sir.json')
    assert len(tm.templates) == 2