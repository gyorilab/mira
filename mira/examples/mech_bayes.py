"""A curated model describing the Msch Bayes model from the paper:
https://www.medrxiv.org/content/10.1101/2020.12.22.20248736v2
https://github.com/dsheldon/mechbayes

The model is a SEIRD model.

NOTE: Currently does not contain rate laws
"""
from mira.metamodel import ControlledConversion, \
    NaturalConversion, Concept
from mira.metamodel.template_model import TemplateModel
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

# dying - in the paper they have the D1 and D2, where D1 is a patient that
# will eventually die, and D2 is the actual death stage.
# uberon:0000071 = "death stage"
dying = Concept(
    name="death stage",
    identifiers={"uberon": "0000071"},
    context={"description": "End of the life of an organism."}
)
# I -> D1
dying_process = NaturalConversion(
    subject=infected,
    outcome=dying,
)
# D1 -> D2
dying_to_death = NaturalConversion(
    subject=dying,
    outcome=dead,
)

# death
# death = NaturalConversion(
#     subject=infected,
#     outcome=dead,
# )

seird = TemplateModel(
    templates=[
        exposure,
        infection,
        recovery,
        dying_process,
        dying_to_death,
    ],
)

