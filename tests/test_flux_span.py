import os
import json
from mira.sources.askenet.flux_span import reproduce_ode_semantics

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'sir_flux_span.json')


def test_flux_span_ode_semantics():
    with open(DATA) as fh:
        flux_span = json.load(fh)
    tm = reproduce_ode_semantics(flux_span)
    assert len(tm.templates) == 10
    assert len(tm.parameters) == 4
    assert all(t.rate_law for t in tm.templates)