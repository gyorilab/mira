from mira.metamodel.composition import compose_two_models, compose
from mira.metamodel.template_model import TemplateModel
from mira.metamodel.templates import *
from mira.examples.concepts import *

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
