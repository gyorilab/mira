from mira.examples.sir import sir_parameterized, sir
from mira.examples.concepts import susceptible
from mira.metamodel import *
from mira.modeling import Model
from mira.modeling.askenet.petrinet import AskeNetPetriNetModel


def test_export():
    pm = AskeNetPetriNetModel(Model(sir_parameterized))
    pm.to_pydantic()
    tm = template_model_from_askenet_json(pm.to_json())

    # Test parameters
    assert 'beta' in tm.parameters
    assert tm.parameters['beta'].value == 0.1
    assert 'gamma' in tm.parameters
    assert tm.parameters['gamma'].value == 0.2

    # Test transitions
    c1, c2 = sorted([t for t in tm.templates], key=lambda s: s.__class__.__name__)
    assert isinstance(c1, ControlledConversion)
    assert c1.subject.name == "susceptible_population"
    assert 'ido' in c1.subject.identifiers
    assert c1.subject.identifiers['ido'] == '0000514'

    assert isinstance(c2, NaturalConversion)

    # Test initials
    assert 'susceptible_population' in tm.initials
    assert tm.initials['susceptible_population'].value == 1
    assert tm.initials['susceptible_population'].concept.name == \
           "susceptible_population"
    assert 'ido' in tm.initials['susceptible_population'].concept.identifiers
    assert tm.initials['susceptible_population'].concept.identifiers['ido'] \
           == '0000514'
    assert len(tm.templates) == 2
