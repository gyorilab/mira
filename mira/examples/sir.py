"""Examples of metamodel templates and other model structures"""

import sympy

from ..metamodel import Concept, ControlledConversion, NaturalConversion
from ..metamodel.templates import TemplateModel

__all__ = [
    "sir",
    "sir_2_city",
    "sir_bilayer",
    "sir_parameterized"
]

# SIR Model
susceptible = Concept(name="susceptible population", identifiers={"ido": "0000514"})
infected = Concept(name="infected population", identifiers={"ido": "0000511"})
recovered = Concept(name="immune population", identifiers={"ido": "0000592"})
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

locals = {
    'susceptible population': sympy.Symbol('susceptible population'),
    'infected population': sympy.Symbol('infected population'),
    'immune population': sympy.Symbol('immune population'),
    'beta': sympy.Symbol('beta'),
    'gamma': sympy.Symbol('gamma')
}

sir_parameterized = TemplateModel(
    templates=[
        ControlledConversion(
            subject=susceptible,
            outcome=infected,
            controller=infected,
            rate_law=(locals['beta'] * locals['susceptible population'] *
                      locals['infected population'])
        ),
        NaturalConversion(
            subject=infected,
            outcome=recovered,
            rate_law=(locals['gamma'] * locals['infected population'] *
                      locals['immune population'])
        )
    ],
    parameters={
        'beta': 0.1,
        'gamma': 0.2
    },
    initials={
        'susceptible population': 1,
        'infected population': 2,
        'immune population': 3
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
