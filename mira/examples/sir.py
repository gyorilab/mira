"""Examples of metamodel templates and other model structures"""

from copy import deepcopy as _d

import sympy

from ..metamodel import ControlledConversion, NaturalConversion, \
    TemplateModel, Parameter, Initial, GroupedControlledConversion
from .concepts import susceptible, infected, recovered, infected_symptomatic, infected_asymptomatic


__all__ = [
    "sir",
    "sir_2_city",
    "sir_bilayer",
    "sir_parameterized",
    "svir",
]

# SIR Model
infection = ControlledConversion(
    subject=susceptible,
    outcome=infected,
    controller=infected,
)
recovery = NaturalConversion(
    subject=infected,
    outcome=recovered,
)
sir = TemplateModel(
    templates=[
        infection,
        recovery,
    ],
)

sir_parameterized = TemplateModel(
    templates=[
        ControlledConversion(
            subject=_d(susceptible),
            outcome=_d(infected),
            controller=_d(infected),
            rate_law=sympy.parse_expr(
                'beta * susceptible_population * infected_population',
                local_dict={'beta': sympy.Symbol('beta')}
            )
        ),
        NaturalConversion(
            subject=_d(infected),
            outcome=_d(recovered),
            rate_law=sympy.parse_expr(
                'gamma * infected_population',
                local_dict={'gamma': sympy.Symbol('gamma')}
            )
        )
    ],
    parameters={
        'beta': Parameter(name='beta', value=0.1),
        'gamma': Parameter(name='gamma', value=0.2)
    },
    initials={
        'susceptible_population': Initial(concept=_d(susceptible), value=1),
        'infected_population': Initial(concept=_d(infected), value=2),
        'immune_population': Initial(concept=_d(recovered), value=3),
    }
)

# SIR 2 City Model
cities = [
    "geonames:5128581",  # NYC
    "geonames:4930956",  # boston
]
susceptible_nyc, susceptible_boston = (susceptible.with_context(city=city) for city in cities)
infected_nyc, infected_boston = (infected.with_context(city=city) for city in cities)
recovered_nyc, recovered_boston = (recovered.with_context(city=city) for city in cities)
infection_nyc, infection_boston = (infection.with_context(city=city) for city in cities)
recovery_nyc, recovery_boston = (recovery.with_context(city=city) for city in cities)
susceptible_nyc_to_boston = NaturalConversion(subject=susceptible_nyc, outcome=susceptible_boston)
susceptible_boston_to_nyc = NaturalConversion(subject=susceptible_boston, outcome=susceptible_nyc)
infected_nyc_to_boston = NaturalConversion(subject=infected_nyc, outcome=infected_boston)
infected_boston_to_nyc = NaturalConversion(subject=infected_boston, outcome=infected_nyc)
recovered_nyc_to_boston = NaturalConversion(subject=recovered_nyc, outcome=recovered_boston)
recovered_boston_to_nyc = NaturalConversion(subject=recovered_boston, outcome=recovered_nyc)
sir_2_city = TemplateModel(
    templates=[
        infection_nyc,
        infection_boston,
        recovery_nyc,
        recovery_boston,
        susceptible_nyc_to_boston,
        susceptible_boston_to_nyc,
        infected_nyc_to_boston,
        infected_boston_to_nyc,
        recovered_nyc_to_boston,
        recovered_boston_to_nyc,
    ],
)

sir_bilayer = \
    {"Wa": [{"influx": 1, "infusion": 2},
            {"influx": 2, "infusion": 3}],
     "Win": [{"arg": 1, "call": 1},
             {"arg": 2, "call": 1},
             {"arg": 2, "call": 2}],
     "Box": [{"parameter": "beta"},
             {"parameter": "gamma"}],
     "Qin": [{"variable": "S"},
             {"variable": "I"},
             {"variable": "R"}],
     "Qout": [{"tanvar": "S'"},
              {"tanvar": "I'"},
              {"tanvar": "R'"}],
     "Wn": [{"efflux": 1, "effusion": 1},
            {"efflux": 2, "effusion": 2}]}


infection_symptomatic = GroupedControlledConversion(
    subject=susceptible,
    outcome=infected_symptomatic,
    controllers=[infected_symptomatic, infected_asymptomatic],
)
infection_asymptomatic = GroupedControlledConversion(
    subject=susceptible,
    outcome=infected_asymptomatic,
    controllers=[infected_symptomatic, infected_asymptomatic],
)
recovery = NaturalConversion(
    subject=infected,
    outcome=recovered,
)
svir = TemplateModel(
    templates=[
        infection_symptomatic,
        infection_asymptomatic,
    ],
)
