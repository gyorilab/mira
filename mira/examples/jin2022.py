"""Implemenation of vaccine-stratified model, shown in figure 2.

.. warning::

    This does not yet include rate laws, which create more complex control
    than the simple flow in the graphical part of the model.
"""

from mira.metamodel import NaturalConversion
from mira.metamodel.templates import ControlledConversion
from mira.metamodel.template_model import TemplateModel
from.concepts import susceptible, infected, recovered, exposed, dead

__all__ = [
    "seir",
    "seird_stratified",
]

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

# fix control structure so when you stratify a controller,
# all of the resulting strata become multiple controllers
templates = []
for template in (infection, recovery):
    templates.extend(
        (
            template.with_context(vaccination_status="vaccinated"),
            template.with_context(vaccination_status="unvaccinated"),
        )
    )

templates.extend(
    (
        exposure.with_context(vaccination_status="vaccinated").add_controller(
            infected.with_context(vaccination_status="unvaccinated")
        ),
        exposure.with_context(vaccination_status="unvaccinated").add_controller(
            infected.with_context(vaccination_status="vaccinated")
        ),
    )
)

for vaccination_status in ["vaccinated", "unvaccinated"]:
    subject = infected.with_context(vaccination_status=vaccination_status)
    templates.append(NaturalConversion(subject=subject, outcome=dead))

seird_stratified = TemplateModel(templates=templates)


def _main():
    from mira.modeling.viz import GraphicalModel
    from pathlib import Path

    gm = GraphicalModel.from_template_model(seird_stratified)
    gm.write(Path.home().joinpath("Desktop", "seird_stratified.png"))


if __name__ == "__main__":
    _main()
