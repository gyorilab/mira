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

S1 = Concept(name="Susceptible", identifiers={"ido": "0000514"})
I1 = Concept(name="Infected", identifiers={"ido": "0000511"})
R1 = Concept(name="Recovery", identifiers={"ido": "0000592"})

S2 = Concept(name="Susceptible", identifiers={"ido": "0000513"})
I2 = Concept(name="Infected", identifiers={"ido": "0000512"})
R2 = Concept(name="Recovery", identifiers={"ido": "0000593"})

S3 = Concept(name="S", identifiers={"ido": "0000514"})
I3 = Concept(name="I", identifiers={"ido": "0000511"})
R3 = Concept(name="R", identifiers={"ido": "0000592"})

S4 = Concept(name="S")
I4 = Concept(name="I")
R4 = Concept(name="R")

model_A1 = TemplateModel(
    templates=[
        ControlledConversion(
            name="Infection", subject=S1, outcome=I1, controller=I1
        )
    ]
)

model_B1 = TemplateModel(
    templates=[NaturalConversion(name="Recovery", subject=I1, outcome=R1)]
)

model_B2 = TemplateModel(
    templates=[NaturalConversion(name="Recovery", subject=I2, outcome=R2)]
)

model_B3 = TemplateModel(
    templates=[NaturalConversion(name="Recovery", subject=I3, outcome=R3)]
)

model_B4 = TemplateModel(
    templates=[NaturalConversion(name="Recovery", subject=I4, outcome=R4)]
)

model_A3 = TemplateModel(
    templates=[
        ControlledConversion(
            name="Infection", subject=S3, outcome=I3, controller=I3
        )
    ]
)

model_A4 = TemplateModel(
    templates=[
        ControlledConversion(
            name="Infection", subject=S4, outcome=I4, controller=I4
        )
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


def test_concept_composition():
    """We test model composition's consolidation of concepts using test-cases
    described in this issue here: https://github.com/gyorilab/mira/issues/409
    """
    model_ab11 = compose([model_A1, model_B1])
    model_ab12 = compose([model_A1, model_B2])
    model_ab13 = compose([model_A1, model_B3])
    model_ab34 = compose([model_A3, model_B4])
    model_ab44 = compose([model_A4, model_B4])

    assert len(model_ab11.get_concepts_map()) == 3
    assert len(model_ab12.get_concepts_map()) == 4
    assert len(model_ab13.get_concepts_map()) == 3
    assert len(model_ab34.get_concepts_map()) == 3
    assert len(model_ab44.get_concepts_name_map()) == 3

    # model_A1 and model_B1's respective infected compartments have same name
    # and identifiers, they should be composed
    assert model_ab11.templates[0].subject.name == "Infected"
    assert model_ab11.templates[0].subject.identifiers == {"ido": "0000511"}

    assert model_ab11.templates[1].outcome.name == "Infected"
    assert model_ab11.templates[1].controller.name == "Infected"
    assert model_ab11.templates[1].outcome.identifiers == {"ido": "0000511"}
    assert model_ab11.templates[1].controller.identifiers == {"ido": "0000511"}

    # model_A1 and model_B2's respective infected compartments have separate identifiers
    # they should be treated as separate concepts and not composed
    assert model_ab12.templates[0].outcome.name == "Infected"
    assert model_ab12.templates[0].controller.name == "Infected"
    assert model_ab12.templates[0].outcome.identifiers == {"ido": "0000511"}
    assert model_ab12.templates[0].controller.identifiers == {"ido": "0000511"}

    assert model_ab12.templates[1].subject.name == "Infected"
    assert model_ab12.templates[1].subject.identifiers == {"ido": "0000512"}

    # model_A1 and model_B3 share an infected compartment with the same identifiers
    # "Infected" for model_A1 and "I" for model_B3
    # since model_A1 is the first model passed in, we prioritize model_A1's
    # infected compartment and test to see if appropriate concept replacement has taken place
    assert model_ab13.templates[0].subject.name == "Infected"
    assert model_ab13.templates[1].outcome.name == "Infected"
    assert model_ab13.templates[1].controller.name == "Infected"

    # model_A3 contains infected component "I" with identifiers
    # model_B4 contains infected compartment "Infected" with no identifiers
    # model_A3 is the first model passed in so we expect the composed model's
    # infected compartment's name to be "I" with identifier present
    assert model_ab34.templates[0].outcome.name == "I"
    assert model_ab34.templates[0].controller.name == "I"
    assert model_ab34.templates[1].subject.name == "I"
    assert model_ab34.templates[0].outcome.identifiers == {"ido": "0000511"}
    assert model_ab34.templates[0].controller.identifiers == {"ido": "0000511"}
    assert model_ab34.templates[1].subject.identifiers == {"ido": "0000511"}

    # model_A4 and model_B4's respective infected compartment share the same name,
    # "I" and neither has an identifier.
    # They should be treated as the same compartment.

    # This tests to see if the two infected compartments are composed into one
    # If treated as separate compartments, then the number of templates will be 3
    assert len(model_ab44.templates) == 2
    assert model_ab44.templates[0].subject.name == "I"
    assert model_ab44.templates[1].outcome.name == "I"
    assert model_ab44.templates[1].controller.name == "I"
