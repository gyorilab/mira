import requests
from pathlib import Path

import sympy

from mira.sources.system_dynamics.pysd import with_lookup_to_piecewise
from mira.sources.system_dynamics.vensim import *
from mira.sources.system_dynamics.stella import *
from mira.modeling.amr.stockflow import template_model_to_stockflow_json
from mira.metamodel import *
from mira.modeling import Model
from mira.metamodel.utils import safe_parse_expr

MDL_SIR_URL = "https://raw.githubusercontent.com/SDXorg/test-models/master/samples/SIR/SIR.mdl"
MDL_LOTKA_URL = (
    "https://raw.githubusercontent.com/SDXorg/test-models/master/samples/Lotka_"
    "Volterra/Lotka_Volterra.mdl"
)
MDL_TEA_URL = "https://raw.githubusercontent.com/SDXorg/test-models/master/samples/teacup/teacup.mdl"

XMILE_SIR_URL = "https://raw.githubusercontent.com/SDXorg/test-models/master/samples/SIR/SIR.xmile"
XMILE_TEA_URL = "https://raw.githubusercontent.com/SDXorg/test-models/master/samples/teacup/teacup.xmile"
XMILE_COVID_URL = "https://exchange.iseesystems.com/model/isee/covid-19-model"
XMILE_RESOURCES_POP_URL = (
    "https://exchange.iseesystems.com/model/isee/resources-and-population"
)

HERE = Path(__file__).parent
MDL_SIR_PATH = HERE / "SIR.mdl"
XMILE_SIR_PATH = HERE / "SIR.xmile"


def test_sir_vensim_file():
    data = requests.get(MDL_SIR_URL).content
    with open(MDL_SIR_PATH, "wb") as file:
        file.write(data)
    tm = template_model_from_mdl_file(MDL_SIR_PATH)
    sir_tm_test(tm)


def test_sir_vensim_url():
    tm = template_model_from_mdl_url(MDL_SIR_URL)
    sir_tm_test(tm)


def test_lotka_vensim_url():
    tm = template_model_from_mdl_url(MDL_LOTKA_URL)


def test_sir_stella_file():
    data = requests.get(XMILE_SIR_URL).content
    with open(XMILE_SIR_PATH, "wb") as file:
        file.write(data)
    tm = template_model_from_stella_model_file(XMILE_SIR_PATH)
    sir_tm_test(tm)


def test_sir_stella_url():
    tm = template_model_from_stella_model_url(XMILE_SIR_URL)
    sir_tm_test(tm)


def test_sir_vensim_end_to_end():
    tm = template_model_from_mdl_url(MDL_SIR_URL)
    model = Model(tm)
    amr = template_model_to_stockflow_json(tm)
    sir_end_to_end_test(model, amr)


def test_sir_stella_end_to_end():
    tm = template_model_from_stella_model_url(XMILE_SIR_URL)
    model = Model(tm)
    amr = template_model_to_stockflow_json(tm)
    sir_end_to_end_test(model, amr)


def test_tea_vensim_end_to_end():
    tm = template_model_from_mdl_url(MDL_TEA_URL)
    model = Model(tm)
    amr = template_model_to_stockflow_json(tm)
    tea_end_to_end_test(model, amr)


def test_tea_stella_end_to_end():
    tm = template_model_from_stella_model_url(XMILE_TEA_URL)
    model = Model(tm)
    amr = template_model_to_stockflow_json(tm)
    tea_end_to_end_test(model, amr)


def sir_tm_test(tm):
    assert len(tm.templates) == 2
    assert len(tm.parameters) == 3
    assert len(tm.initials) == 3

    assert isinstance(tm.templates[0], ControlledConversion)
    assert isinstance(tm.templates[1], NaturalConversion)

    assert "susceptible" in tm.initials
    assert "infectious" in tm.initials
    assert "recovered" in tm.initials
    assert tm.initials["susceptible"].expression == SympyExprStr(
        sympy.Float(1000)
    )
    assert tm.initials["infectious"].expression == SympyExprStr(sympy.Float(5))
    assert tm.initials["recovered"].expression == SympyExprStr(sympy.Float(0))

    assert "contact_infectivity" in tm.parameters
    assert "duration" in tm.parameters
    assert "total_population" in tm.parameters
    assert tm.parameters["contact_infectivity"].value == 0.3
    assert tm.parameters["duration"].value == 5.0
    assert tm.parameters["total_population"].value == 1000

    assert tm.templates[0].subject.name == "susceptible"
    assert tm.templates[0].outcome.name == "infectious"
    assert tm.templates[0].controller.name == "infectious"

    assert tm.templates[1].subject.name == "infectious"
    assert tm.templates[1].outcome.name == "recovered"


def sir_end_to_end_test(model, amr):
    assert len(model.transitions) == 2
    assert len(model.variables) == 3
    assert len(model.parameters) - 1 == 3
    assert "infectious" in model.variables
    assert "recovered" in model.variables
    assert "susceptible" in model.variables
    assert "duration" in model.parameters
    assert "contact_infectivity" in model.parameters
    assert "total_population" in model.parameters

    amr_model = amr["model"]
    amr_semantics_ode = amr["semantics"]["ode"]
    assert len(amr_model["flows"]) == 2
    assert len(amr_model["stocks"]) == 3
    assert len(amr_model["auxiliaries"]) == 3
    assert len(amr_model["links"]) == 6
    assert len(amr_semantics_ode["parameters"]) == 3
    assert len(amr_semantics_ode["initials"]) == 3

    assert amr_model["flows"][0]["upstream_stock"] == "susceptible"
    assert amr_model["flows"][0]["downstream_stock"] == "infectious"
    assert amr_model["flows"][0]["name"] == "succumbing"
    assert amr_model["flows"][1]["upstream_stock"] == "infectious"
    assert amr_model["flows"][1]["downstream_stock"] == "recovered"
    assert amr_model["flows"][1]["name"] == "recovering"

    assert safe_parse_expr(
        amr_model["flows"][0]["rate_expression"]
    ) == safe_parse_expr(
        "infectious*susceptible*contact_infectivity/total_population"
    )
    assert safe_parse_expr(
        amr_model["flows"][1]["rate_expression"]
    ) == safe_parse_expr("infectious/duration")

    assert amr_model["stocks"][0]["name"] == "susceptible"
    assert amr_model["stocks"][1]["name"] == "infectious"
    assert amr_model["stocks"][2]["name"] == "recovered"

    assert amr_model["auxiliaries"][0]["name"] == "contact_infectivity"
    assert amr_model["auxiliaries"][1]["name"] == "total_population"
    assert amr_model["auxiliaries"][2]["name"] == "duration"

    assert amr_semantics_ode["parameters"][0]["id"] == "contact_infectivity"
    assert amr_semantics_ode["parameters"][0]["value"] == 0.3
    assert amr_semantics_ode["parameters"][1]["id"] == "total_population"
    assert amr_semantics_ode["parameters"][1]["value"] == 1000.0
    assert amr_semantics_ode["parameters"][2]["id"] == "duration"
    assert amr_semantics_ode["parameters"][2]["value"] == 5.0

    assert amr_semantics_ode["initials"][0]["target"] == "susceptible"
    assert float(amr_semantics_ode["initials"][0]["expression"]) == 1000.0
    assert amr_semantics_ode["initials"][1]["target"] == "infectious"
    assert float(amr_semantics_ode["initials"][1]["expression"]) == 5.0
    assert amr_semantics_ode["initials"][2]["target"] == "recovered"
    assert float(amr_semantics_ode["initials"][2]["expression"]) == 0.0


def tea_end_to_end_test(model, amr):
    assert len(model.transitions) == 1
    assert len(model.variables) == 1
    assert len(model.parameters) - 1 == 2
    assert "teacup_temperature" in model.variables
    assert "characteristic_time" in model.parameters
    assert "room_temperature" in model.parameters

    amr_model = amr["model"]
    amr_semantics_ode = amr["semantics"]["ode"]
    assert len(amr_model["flows"]) == 1
    assert len(amr_model["stocks"]) == 1
    assert len(amr_model["auxiliaries"]) == 2
    assert len(amr_model["links"]) == 3
    assert len(amr_semantics_ode["parameters"]) == 2
    assert len(amr_semantics_ode["initials"]) == 1

    assert amr_model["flows"][0]["upstream_stock"] == "teacup_temperature"
    assert amr_model["flows"][0]["downstream_stock"] is None
    assert amr_model["flows"][0]["name"] == "heat_loss_to_room"

    assert safe_parse_expr(
        amr_model["flows"][0]["rate_expression"]
    ) == safe_parse_expr(
        "(teacup_temperature - room_temperature)/characteristic_time"
    )

    assert amr_model["stocks"][0]["name"] == "teacup_temperature"

    assert amr_model["auxiliaries"][0]["name"] == "characteristic_time"
    assert amr_model["auxiliaries"][1]["name"] == "room_temperature"

    assert amr_semantics_ode["parameters"][0]["id"] == "characteristic_time"
    assert amr_semantics_ode["parameters"][0]["value"] == 10.0
    assert amr_semantics_ode["parameters"][1]["id"] == "room_temperature"
    assert amr_semantics_ode["parameters"][1]["value"] == 70.0
    assert amr_semantics_ode["initials"][0]["target"] == "teacup_temperature"
    assert float(amr_semantics_ode["initials"][0]["expression"]) == 180.0


def test_stella_resources_pop_model():
    tm = template_model_from_stella_model_url(XMILE_RESOURCES_POP_URL)
    assert len(tm.initials) == 2
    assert "natural_resources" in tm.initials
    assert "population" in tm.initials

    assert len(tm.templates) == 4

    assert isinstance(tm.templates[0], NaturalProduction)
    assert tm.templates[0].outcome.name == "natural_resources"

    assert isinstance(tm.templates[1], NaturalDegradation)
    assert tm.templates[1].subject.name == "natural_resources"

    assert isinstance(tm.templates[2], NaturalProduction)
    assert tm.templates[2].outcome.name == "population"

    assert isinstance(tm.templates[3], NaturalDegradation)
    assert tm.templates[3].subject.name == "population"


def test_stella_covid19_model():
    tm = template_model_from_stella_model_url(XMILE_COVID_URL)

    assert len(tm.initials) == 15
    assert "uninfected_at_risk" in tm.initials
    assert "infected_not_contagious" in tm.initials
    assert "asymptomatic_contagious" in tm.initials
    assert "symptomatic_contagious" in tm.initials
    assert "symptomatic_not_contagious" in tm.initials
    assert "recovered" in tm.initials
    assert "tested_infected_not_contagious" in tm.initials
    assert "tested_asymptomatic_contagious" in tm.initials
    assert "tested_symptomatic_contagious" in tm.initials
    assert "tested_symptomatic_not_contagious" in tm.initials
    assert "tested_infected" in tm.initials
    assert "presumed_infected" in tm.initials
    assert "cumulative_deaths" in tm.initials
    assert "hospital_bed_days" in tm.initials
    assert "cumulative_testing" in tm.initials

    assert len(tm.templates) == 23

    assert isinstance(tm.templates[0], NaturalProduction)
    assert tm.templates[0].outcome.name == "cumulative_deaths"

    assert isinstance(tm.templates[1], NaturalProduction)
    assert tm.templates[1].outcome.name == "cumulative_testing"

    assert isinstance(tm.templates[2], NaturalProduction)
    assert tm.templates[2].outcome.name == "hospital_bed_days"

    assert isinstance(tm.templates[3], NaturalConversion)
    assert tm.templates[3].subject.name == "uninfected_at_risk"
    assert tm.templates[3].outcome.name == "infected_not_contagious"

    assert isinstance(tm.templates[4], NaturalConversion)
    assert tm.templates[4].subject.name == "infected_not_contagious"
    assert tm.templates[4].outcome.name == "asymptomatic_contagious"

    assert isinstance(tm.templates[5], NaturalConversion)
    assert tm.templates[5].subject.name == "asymptomatic_contagious"
    assert tm.templates[5].outcome.name == "symptomatic_contagious"

    assert isinstance(tm.templates[6], NaturalConversion)
    assert tm.templates[6].subject.name == "asymptomatic_contagious"
    assert tm.templates[6].outcome.name == "tested_asymptomatic_contagious"

    assert isinstance(tm.templates[7], NaturalProduction)
    assert tm.templates[7].outcome.name == "infected_not_contagious"

    assert isinstance(tm.templates[8], NaturalConversion)
    assert tm.templates[8].subject.name == "infected_not_contagious"
    assert tm.templates[8].outcome.name == "tested_infected_not_contagious"

    assert isinstance(tm.templates[9], NaturalProduction)
    assert tm.templates[9].outcome.name == "presumed_infected"

    assert isinstance(tm.templates[10], NaturalConversion)
    assert tm.templates[10].subject.name == "symptomatic_not_contagious"
    assert tm.templates[10].outcome.name == "recovered"

    assert isinstance(tm.templates[11], NaturalConversion)
    assert tm.templates[11].subject.name == "tested_symptomatic_not_contagious"
    assert tm.templates[11].outcome.name == "recovered"

    assert isinstance(tm.templates[12], NaturalDegradation)
    assert tm.templates[12].subject.name == "symptomatic_contagious"

    assert isinstance(tm.templates[13], NaturalConversion)
    assert tm.templates[13].subject.name == "symptomatic_contagious"
    assert tm.templates[13].outcome.name == "symptomatic_not_contagious"

    assert isinstance(tm.templates[14], NaturalConversion)
    assert tm.templates[14].subject.name == "symptomatic_contagious"
    assert tm.templates[14].outcome.name == "tested_symptomatic_contagious"

    assert isinstance(tm.templates[15], NaturalDegradation)
    assert tm.templates[15].subject.name == "symptomatic_not_contagious"

    assert isinstance(tm.templates[16], NaturalConversion)
    assert tm.templates[16].subject.name == "symptomatic_not_contagious"
    assert tm.templates[16].outcome.name == "tested_symptomatic_not_contagious"

    assert isinstance(tm.templates[17], NaturalConversion)
    assert tm.templates[17].subject.name == "tested_infected_not_contagious"
    assert tm.templates[17].outcome.name == "tested_asymptomatic_contagious"

    assert isinstance(tm.templates[18], NaturalConversion)
    assert tm.templates[18].subject.name == "tested_asymptomatic_contagious"
    assert tm.templates[18].outcome.name == "tested_symptomatic_contagious"

    assert isinstance(tm.templates[19], NaturalProduction)
    assert tm.templates[19].outcome.name == "tested_infected"

    assert isinstance(tm.templates[20], NaturalDegradation)
    assert tm.templates[20].subject.name == "tested_symptomatic_contagious"

    assert isinstance(tm.templates[21], NaturalConversion)
    assert tm.templates[21].subject.name == "tested_symptomatic_contagious"
    assert tm.templates[21].outcome.name == "tested_symptomatic_not_contagious"

    assert isinstance(tm.templates[22], NaturalDegradation)
    assert tm.templates[22].subject.name == "tested_symptomatic_not_contagious"


def test_with_lookup_to_piecewise():
    data = "WITH LOOKUP(time,([(0,0)-(500,100)],(0,0),(1,2),(2,1),(3,0),(4,2),(5,1),(1000,0)))"
    val = with_lookup_to_piecewise(data)
    rv = safe_parse_expr(val)
    assert isinstance(rv, sympy.Expr)
