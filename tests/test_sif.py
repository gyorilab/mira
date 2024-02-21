from mira.sources.sif import template_model_from_sif_edges
from mira.modeling.amr.regnet import template_model_to_regnet_json


def test_sif_processing():
    # Lotka volterra example
    edges = [
        ('prey', 'POSITIVE', 'predator'),
        ('predator', 'NEGATIVE', 'prey'),
        ('prey', 'POSITIVE', 'prey'),
        ('predator', 'NEGATIVE', 'predator')
    ]
    tm = template_model_from_sif_edges(edges)
    assert len(tm.templates) == 4
    regnet = template_model_to_regnet_json(tm)
    assert len(regnet['model']['edges']) == 2
