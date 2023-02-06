"""CHIME SVIIvR."""

from mira.metamodel import NaturalConversion, ControlledConversion, \
    TemplateModel
from .concepts import susceptible, infected, recovered

infection = ControlledConversion(
    subject=susceptible,
    outcome=infected,
    controller=infected,
)

templates = []
templates.append(
    infection.with_context(vaccination_status="vaccinated").add_controller(
        infected.with_context(vaccination_status="unvaccinated")
    )
)
templates.append(
    infection.with_context(vaccination_status="unvaccinated").add_controller(
        infected.with_context(vaccination_status="vaccinated")
    )
)

for vaccination_status in ["vaccinated", "unvaccinated"]:
    subject = infected.with_context(vaccination_status=vaccination_status)
    templates.append(NaturalConversion(subject=subject, outcome=recovered))

sviivr = TemplateModel(templates=templates)


def _main():
    from mira.modeling.viz import GraphicalModel
    from pathlib import Path

    gm = GraphicalModel.from_template_model(sviivr)
    gm.write(Path.home().joinpath("Desktop", "sviivr.png"))


if __name__ == "__main__":
    _main()
