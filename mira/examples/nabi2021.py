"""This includes the model described by Nabi *et al.* (2021) in
`Projections and fractional dynamics of COVID-19 with optimal control
strategies <https://doi.org/10.1016/j.chaos.2021.110689>`_.
"""

from mira.metamodel import Concept, GroupedControlledConversion, NaturalConversion
from mira.metamodel.template_model import TemplateModel

__all__ = [
    "nabi2021",
]

susceptible = Concept(name="Susceptible (S)")
exposed_1 = Concept(name="Exposed (E_1)")
exposed_2 = Concept(name="Pre-symptomatic Infectious (E_2)")
asymptomatic_infectious = Concept(name="Asymptomatic Infectious (A)")
symptomatic_infectious = Concept(name="Symptomatic Infectious (I)")
quarantined = Concept(name="Quarantined (Q)")
isolated = Concept(name="Isolated (L)")
recovered = Concept(name="Recovered (R)")
dead = Concept(name="Disease-induced Death (D)")

s_e1 = GroupedControlledConversion(
    subject=susceptible,
    outcome=exposed_1,
    controllers=[
        symptomatic_infectious,
        asymptomatic_infectious,
        quarantined,
        isolated,
        exposed_2,
    ],
)

e1_e2 = NaturalConversion(subject=exposed_1, outcome=exposed_2)
e2_a = NaturalConversion(subject=exposed_2, outcome=asymptomatic_infectious)
e2_i = NaturalConversion(subject=exposed_2, outcome=symptomatic_infectious)
e2_q = NaturalConversion(subject=exposed_2, outcome=quarantined)

a_l = NaturalConversion(subject=asymptomatic_infectious, outcome=isolated)
a_r = NaturalConversion(subject=asymptomatic_infectious, outcome=recovered)
i_l = NaturalConversion(subject=symptomatic_infectious, outcome=isolated)
i_r = NaturalConversion(subject=symptomatic_infectious, outcome=recovered)
i_d = NaturalConversion(subject=symptomatic_infectious, outcome=dead)
q_r = NaturalConversion(subject=quarantined, outcome=recovered)
q_d = NaturalConversion(subject=quarantined, outcome=dead)
l_r = NaturalConversion(subject=isolated, outcome=recovered)
l_d = NaturalConversion(subject=isolated, outcome=dead)

nabi2021 = TemplateModel(
    templates=[s_e1, e1_e2, e2_a, e2_i, e2_q, a_l, a_r, i_l, i_r, i_d, q_r, q_d, l_r, l_d]
)
