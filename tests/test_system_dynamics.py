import requests
from pathlib import Path

import sympy

from mira.sources.system_dynamics.pysd import (
    with_lookup_to_piecewise,
    ifthenelse_to_piecewise,
)
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


# def test_eval():
#     url = "https://raw.githubusercontent.com/DARPA-ASKEM/program-milestones/main/18-month-milestone/evaluation/Epi%20Use%20Case/Scenario%204%20Supplementary/stock_flow_evaluation.mdl"
#     tm = template_model_from_mdl_url(url)


def test_sir_vensim_file():
    data = requests.get(MDL_SIR_URL).content
    with open(MDL_SIR_PATH, "wb") as file:
        file.write(data)
    tm = template_model_from_mdl_file(MDL_SIR_PATH)
    sir_tm_test(tm, is_vensim=True)


def test_sir_vensim_url():
    tm = template_model_from_mdl_url(MDL_SIR_URL)
    sir_tm_test(tm, is_vensim=True)


def test_lotka_vensim_url():
    tm = template_model_from_mdl_url(MDL_LOTKA_URL)


def test_sir_stella_file():
    data = requests.get(XMILE_SIR_URL).content
    with open(XMILE_SIR_PATH, "wb") as file:
        file.write(data)
    tm = template_model_from_stella_model_file(XMILE_SIR_PATH)
    sir_tm_test(tm, is_vensim=False)


def test_sir_stella_url():
    tm = template_model_from_stella_model_url(XMILE_SIR_URL)
    sir_tm_test(tm, is_vensim=False)


def test_sir_vensim_end_to_end():
    tm = template_model_from_mdl_url(MDL_SIR_URL)
    model = Model(tm)
    amr = template_model_to_stockflow_json(tm)
    sir_end_to_end_test(model, amr, is_vensim=True)


def test_sir_stella_end_to_end():
    tm = template_model_from_stella_model_url(XMILE_SIR_URL)
    model = Model(tm)
    amr = template_model_to_stockflow_json(tm)
    sir_end_to_end_test(model, amr, is_vensim=False)


def test_tea_vensim_end_to_end():
    tm = template_model_from_mdl_url(MDL_TEA_URL)
    model = Model(tm)
    amr = template_model_to_stockflow_json(tm)
    tea_end_to_end_test(model, amr, is_vensim=True)


def test_tea_stella_end_to_end():
    tm = template_model_from_stella_model_url(XMILE_TEA_URL)
    model = Model(tm)
    amr = template_model_to_stockflow_json(tm)
    tea_end_to_end_test(model, amr, is_vensim=False)


def sir_tm_test(tm, is_vensim):
    assert len(tm.templates) == 2
    if is_vensim is False:
        assert len(tm.parameters) == 3
    else:
        assert len(tm.parameters) == 6
    assert len(tm.initials) == 3

    assert isinstance(tm.templates[0], NaturalConversion)
    assert isinstance(tm.templates[1], ControlledConversion)

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

    assert tm.templates[0].subject.name == "infectious"
    assert tm.templates[0].outcome.name == "recovered"

    assert tm.templates[1].subject.name == "susceptible"
    assert tm.templates[1].outcome.name == "infectious"
    assert tm.templates[1].controller.name == "infectious"


def sir_end_to_end_test(model, amr, is_vensim):
    assert len(model.transitions) == 2
    assert len(model.variables) == 3
    if is_vensim is False:
        assert len(model.parameters) - 1 == 3
    else:
        assert len(model.parameters) - 1 == 6
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
    if is_vensim is False:
        assert len(amr_semantics_ode["parameters"]) == 3
    else:
        assert len(amr_semantics_ode["parameters"]) == 6

    assert len(amr_semantics_ode["initials"]) == 3

    assert amr_model["flows"][0]["upstream_stock"] == "infectious"
    assert amr_model["flows"][0]["downstream_stock"] == "recovered"
    assert amr_model["flows"][0]["name"] == "recovering"
    assert amr_model["flows"][1]["upstream_stock"] == "susceptible"
    assert amr_model["flows"][1]["downstream_stock"] == "infectious"
    assert amr_model["flows"][1]["name"] == "succumbing"

    assert safe_parse_expr(
        amr_model["flows"][0]["rate_expression"]
    ) == safe_parse_expr("infectious/duration")

    assert safe_parse_expr(
        amr_model["flows"][1]["rate_expression"]
    ) == safe_parse_expr(
        "infectious*susceptible*contact_infectivity/total_population"
    )

    assert amr_model["stocks"][0]["name"] == "infectious"
    assert amr_model["stocks"][1]["name"] == "recovered"
    assert amr_model["stocks"][2]["name"] == "susceptible"

    assert amr_model["auxiliaries"][0]["name"] == "duration"
    assert amr_model["auxiliaries"][1]["name"] == "contact_infectivity"
    assert amr_model["auxiliaries"][2]["name"] == "total_population"

    assert amr_semantics_ode["parameters"][0]["id"] == "duration"
    assert amr_semantics_ode["parameters"][0]["value"] == 5.0
    assert amr_semantics_ode["parameters"][1]["id"] == "contact_infectivity"
    assert amr_semantics_ode["parameters"][1]["value"] == 0.3
    assert amr_semantics_ode["parameters"][2]["id"] == "total_population"
    assert amr_semantics_ode["parameters"][2]["value"] == 1000.0

    assert amr_semantics_ode["initials"][0]["target"] == "infectious"
    assert float(amr_semantics_ode["initials"][0]["expression"]) == 5.0
    assert amr_semantics_ode["initials"][1]["target"] == "recovered"
    assert float(amr_semantics_ode["initials"][1]["expression"]) == 0.0
    assert amr_semantics_ode["initials"][2]["target"] == "susceptible"
    assert float(amr_semantics_ode["initials"][2]["expression"]) == 1000.0


def tea_end_to_end_test(model, amr, is_vensim):
    assert len(model.transitions) == 1
    assert len(model.variables) == 1
    if is_vensim is False:
        assert len(model.parameters) - 1 == 2
    else:
        assert len(model.parameters) - 1 == 5
    assert "teacup_temperature" in model.variables
    assert "characteristic_time" in model.parameters
    assert "room_temperature" in model.parameters

    amr_model = amr["model"]
    amr_semantics_ode = amr["semantics"]["ode"]
    assert len(amr_model["flows"]) == 1
    assert len(amr_model["stocks"]) == 1
    assert len(amr_model["auxiliaries"]) == 2
    assert len(amr_model["links"]) == 3
    if is_vensim is False:
        assert len(amr_semantics_ode["parameters"]) == 2
    else:
        assert len(amr_semantics_ode["parameters"]) == 5
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
    assert tm.templates[0].outcome.name == "population"

    assert isinstance(tm.templates[1], NaturalDegradation)
    assert tm.templates[1].subject.name == "natural_resources"

    assert isinstance(tm.templates[2], NaturalDegradation)
    assert tm.templates[2].subject.name == "population"

    assert isinstance(tm.templates[3], NaturalProduction)
    assert tm.templates[3].outcome.name == "natural_resources"


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


def test_ifthenelse():
    text = "IF THEN ELSE(Density ratio<=1, 1, LOG(Density ratio, 50)+1)"
    val = ifthenelse_to_piecewise(text)
    assert (
        val
        == "Piecewise((1, Density ratio<=1), (LOG(Density ratio, 50)+1, True))"
    )

    text = "IF THEN ELSE(Density ratio<=1, 1, Density ratio+1)"
    val = ifthenelse_to_piecewise(text)
    assert val == "Piecewise((1, Density ratio<=1), (Density ratio+1, True))"


def test_with_lookup_to_piecewise():
    data = "WITH LOOKUP(time,([(0,0)-(500,100)],(0,0),(1,2),(2,1),(3,0),(4,2),(5,1),(1000,0)))"
    val = with_lookup_to_piecewise(data)
    rv = safe_parse_expr(val)
    assert isinstance(rv, sympy.Expr)
