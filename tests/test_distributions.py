import sympy

from mira.metamodel import *
from mira.modeling import Model
from mira.modeling.amr.petrinet import template_model_to_petrinet_json


def test_distribution_expressions():
    beta_mean = Parameter(name='beta_mean',
                          distribution=Distribution(type="Beta1",
                                                    parameters={'alpha': sympy.Integer(1),
                                                                'beta': sympy.Integer(10)}))
    gamma_mean = Parameter(name='gamma_mean',
                           distribution=Distribution(type="Beta1",
                                                     parameters={'alpha': sympy.Integer(10),
                                                                 'beta': sympy.Integer(10)}))
    beta = Parameter(name='beta',
                     distribution=Distribution(type="InverseGamma1",
                                               parameters={'shape': sympy.Symbol('beta_mean'),
                                                           'scale': sympy.Float(0.01)}))
    gamma = Parameter(name='gamma',
                      distribution=Distribution(type="InverseGamma1",
                                                parameters={'shape': sympy.Symbol('gamma_mean'),
                                                            'scale': sympy.Float(0.01)}))

    # Make an SIR model with beta and gamma in rate laws
    sir_model = TemplateModel(
        templates=[
            ControlledConversion(
                subject=Concept(name='S'),
                outcome=Concept(name='I'),
                controller=Concept(name='I'),
                rate_law=sympy.Symbol('S') * sympy.Symbol('I') * sympy.Symbol('beta')
            ),
            NaturalConversion(
                subject=Concept(name='I'),
                outcome=Concept(name='R'),
                rate_law=sympy.Symbol('I') * sympy.Symbol('gamma')
            ),
        ],
        parameters={
            'beta': beta,
            'gamma': gamma,
            'beta_mean': beta_mean,
            'gamma_mean': gamma_mean,
            }
    )

    model = Model(sir_model)
    pn_json = template_model_to_petrinet_json(sir_model)
    print(pn_json)
