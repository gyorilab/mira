"""CHIME SVIIvR."""

from mira.metamodel import Concept, NaturalConversion
from mira.metamodel.templates import ControlledConversion, TemplateModel

susceptible = Concept(
    name="susceptible_population", identifiers={"ido": "0000514"}
)
infected = Concept(name="infected_population", identifiers={"ido": "0000511"})
recovered = Concept(name="recovered", identifiers={"ido": "0000592"})

infection = NaturalConversion(
    subject=susceptible,
    outcome=infected,
)

templates = []
templates.append(infection.with_context(vaccination_status="vaccinated"))
templates.append(infection.with_context(vaccination_status="unvaccinated"))

for vaccination_status in ["vaccinated", "unvaccinated"]:
    subject = infected.with_context(vaccination_status=vaccination_status)
    templates.append(NaturalConversion(subject=subject, outcome=recovered))

sviivr = TemplateModel(templates=templates)
