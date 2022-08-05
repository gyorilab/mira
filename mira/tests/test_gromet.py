from mira.modeling.gromet_model import GroMEtModel
from mira.metamodel import ControlledConversion, Concept, NaturalConversion
from mira.modeling import Model, TemplateModel


def test_init():
    # Sanity check to see that the class can be instantiated
    infected = Concept(name="infected population", identifiers={"ido": "0000511"})
    susceptible = Concept(name="susceptible population", identifiers={"ido": "0000514"})
    immune = Concept(name="immune population", identifiers={"ido": "0000592"})

    t1 = ControlledConversion(
        controller=infected,
        subject=susceptible,
        outcome=infected,
    )
    t2 = NaturalConversion(subject=infected, outcome=immune)
    sir_model_templ = TemplateModel(templates=[t1, t2])
    sir_model = Model(sir_model_templ)
    gromet_model = GroMEtModel(sir_model, "sir_model")
