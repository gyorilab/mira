"""Implemenation of vaccine-stratified model, shown in figure 2."""

from mira.metamodel import Concept, NaturalConversion
from mira.metamodel.templates import ControlledConversion, TemplateModel

__all__ = [
    "seir",
    "seird_stratified",
]

susceptible = Concept(
    name="susceptible_population", identifiers={"ido": "0000514"}
)
infected = Concept(name="infected_population", identifiers={"ido": "0000511"})
recovered = Concept(name="recovered", identifiers={"ido": "0000592"})
exposed = Concept(
    name="exposed", identifiers={"apollosv": "00000154", "ncit": "C71551"}
)
dead = Concept(name="dead", identifiers={"ncit": "C28554"})

exposure = ControlledConversion(
    subject=susceptible,
    outcome=exposed,
    controller=infected,
)
infection = NaturalConversion(
    subject=exposed,
    outcome=infected,
)
recovery = NaturalConversion(
    subject=infected,
    outcome=recovered,
)

seir = TemplateModel(
    templates=[
        exposure,
        infection,
        recovery,
    ],
)

templates = []
for template in (exposure, infection, recovery):
    templates.append(template.with_context(vaccination_status="vaccinated"))
    templates.append(template.with_context(vaccination_status="unvaccinated"))

for vaccination_status in ["vaccinated", "unvaccinated"]:
    templates.append(
        NaturalConversion(
            subject=infection.with_context(
                vaccination_status=vaccination_status
            ),
            outcome=dead,
        )
    )

seird_stratified = TemplateModel(templates=templates)
