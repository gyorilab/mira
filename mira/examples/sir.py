"""Examples of metamodel templates."""

from ..metamodel import Concept, ControlledConversion, NaturalConversion
from ..modeling import TemplateModel

__all__ = [
    "sir",
    "sir_2_city",
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
