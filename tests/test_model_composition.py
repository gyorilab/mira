from mira.metamodel.composition import compose_two_models, compose
from mira.metamodel.template_model import TemplateModel
from mira.metamodel.templates import *
from mira.examples.concepts import *
from mira.sources.amr.petrinet import model_from_url

sir_petrinet_tm = model_from_url(
    "https://raw.githubusercontent.com/DARPA-ASKEM/Model-Representations"
    "/main/petrinet/examples/sir.json")

halfar_petrinet_tm = model_from_url(
    "https://raw.githubusercontent.com/DARPA-ASKEM/Model-Representations"
    "/main/petrinet/examples/halfar.json"
)

infection = ControlledConversion(
    subject=susceptible,
    outcome=infected,
    controller=infected,
)
recovery = NaturalConversion(
    subject=infected,
    outcome=recovered,
)

reinfection = ControlledConversion(
    subject=recovered,
    outcome=infected,
    controller=infected,
)

dying = NaturalConversion(
    subject=infected,
    outcome=dead
)

sir = TemplateModel(
    templates=[
        infection,
        recovery,
    ]
)

mini_sir = TemplateModel(
    templates=[
        recovery
    ]
)

sir_reinfection = TemplateModel(
    templates=[
        infection,
        recovery,
        reinfection
    ]
)

sir_dying = TemplateModel(
    templates=[
        infection,
        dying,
        recovery,
    ]
)


def test_compose_two_models():
    composed_model = compose_two_models(sir_reinfection, sir)
    assert len(composed_model.templates) == 3


def test_compose_list():
    model_list = [sir_reinfection, sir_dying, sir]
    composed_model = compose(model_list)
    assert len(composed_model.templates) == 4


def test_disjoint_models():
    composed_tm = compose_two_models(sir_petrinet_tm, halfar_petrinet_tm)
    assert len(composed_tm.initials) == len(sir_petrinet_tm.initials) + len(
        halfar_petrinet_tm.initials)
    assert len(composed_tm.templates) == len(sir_petrinet_tm.templates) + len(
        halfar_petrinet_tm.templates)
    # shared parameter "gamma"
    assert len(composed_tm.parameters) == len(sir_petrinet_tm.parameters) + len(
        halfar_petrinet_tm.parameters) - 1
    assert (len(composed_tm.observables) == len(sir_petrinet_tm.observables) +
            len(halfar_petrinet_tm.observables))


def test_model_priority():
    """Test to see that we prioritize the first template model passed in and
    checks for observable expression concept replacement"""
    composed_tm_0 = compose_two_models(sir, sir_petrinet_tm)
    assert len(composed_tm_0.templates) == 2
    assert len(composed_tm_0.initials) == 0
    assert len(composed_tm_0.parameters) == 0
    assert len(composed_tm_0.observables) == 1
    assert (str(composed_tm_0.observables["noninf"].expression) ==
            "immune_population + susceptible_population")
    assert composed_tm_0.templates[0].rate_law is None
    assert composed_tm_0.templates[1].rate_law is None

    composed_tm_1 = compose_two_models(sir_petrinet_tm, sir)
    assert len(composed_tm_1.templates) == 2
    assert len(composed_tm_1.initials) == 3
    assert len(composed_tm_1.parameters) == 2
    assert len(composed_tm_1.observables) == 1
    assert str(composed_tm_1.observables["noninf"].expression) == "R + S"
    assert composed_tm_1.templates[0].rate_law
    assert composed_tm_1.templates[1].rate_law


def test_template_inclusion():
    """Test to see that we include all desired templates in the
    composed template model"""
    composed_tm = compose_two_models(mini_sir, sir)
    assert len(composed_tm.templates) == 2
