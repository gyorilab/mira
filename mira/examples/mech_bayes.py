"""A curated model describing the Msch Bayes model from the paper:
https://www.medrxiv.org/content/10.1101/2020.12.22.20248736v2
https://github.com/dsheldon/mechbayes

The model is a SEIRD model.
"""
from mira.metamodel import TemplateModel, ControlledConversion, \
    NaturalConversion
from mira.examples.concepts import susceptible, exposed, infected, recovered, dead

# Define the transitions

# Exposure
exposure = ControlledConversion(
    subject=susceptible,
    outcome=exposed,
    controller=infected,
)

# Infection
infection = NaturalConversion(
    subject=exposed,
    outcome=infected,
)

# recovery
recovery = NaturalConversion(
    subject=infected,
    outcome=recovered,
)

# death
death = NaturalConversion(
    subject=infected,
    outcome=dead,
)

seird = TemplateModel(
    templates=[
        exposure,
        infection,
        recovery,
        death,
    ],
)

