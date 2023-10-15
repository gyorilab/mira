import os
import json
from mira.sources.amr.flux_span import reproduce_ode_semantics
from mira.modeling import Model
from mira.modeling.amr.petrinet import AMRPetriNetModel

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'sir_flux_span.json')


def test_flux_span_ode_semantics():
    with open(DATA) as fh:
        flux_span = json.load(fh)
    tm = reproduce_ode_semantics(flux_span)
    assert len(tm.templates) == 10
    assert len(tm.parameters) == 11
    assert all(t.rate_law for t in tm.templates)
    model = Model(tm)
    am = AMRPetriNetModel(model).to_json()
    # Make sure we preserve transition IDs
    assert am['model']['transitions'][0]['id'] == 'inf1'