from mira.metamodel import *
from mira.sources.askenet import model_from_url
from mira.sources.askenet import petrinet
from mira.sources.askenet import regnet

petrinet_example = 'https://raw.githubusercontent.com/DARPA-ASKEM/' \
    'Model-Representations/main/petrinet/examples/sir.json'
regnet_example = 'https://raw.githubusercontent.com/DARPA-ASKEM/' \
    'Model-Representations/main/regnet/examples/lotka_volterra.json'


def test_petrinet_model_from_url():
    template_model = petrinet.model_from_url(petrinet_example)
    assert len(template_model.templates) == 2
    assert isinstance(template_model.templates[0], ControlledConversion)
    assert isinstance(template_model.templates[1], NaturalConversion)
    assert template_model.templates[0].controller.display_name == 'Infected'
    assert template_model.templates[0].controller.name == 'I'
    assert template_model.templates[0].subject.display_name == 'Susceptible'
    assert template_model.templates[0].outcome.display_name == 'Infected'
    assert template_model.templates[1].subject.display_name == 'Infected'
    assert template_model.templates[1].outcome.display_name == 'Recovered'


def test_regnet_model_from_url():
    template_model = regnet.model_from_url(regnet_example)
    assert len(template_model.templates) == 4
    assert isinstance(template_model.templates[0], ControlledProduction)
    assert isinstance(template_model.templates[1], NaturalDegradation)
    assert isinstance(template_model.templates[2], ControlledDegradation)
    assert isinstance(template_model.templates[3], GroupedControlledProduction)


def test_model_from_url_generic():
    tm = model_from_url(regnet_example)
    assert len(tm.templates) == 4

    tm = model_from_url(petrinet_example)
    assert len(tm.templates) == 2


def test_deg_prod():
    import sympy
    from mira.modeling import Model
    from mira.modeling.askenet.petrinet import AskeNetPetriNetModel

    person_units = lambda: Unit(expression=sympy.Symbol('person'))
    virus_units = lambda: Unit(expression=sympy.Symbol('virus'))
    virus_per_gram_units = lambda: Unit(expression=sympy.Symbol('virus') / sympy.Symbol('gram'))
    day_units = lambda: Unit(expression=sympy.Symbol('day'))
    per_day_units = lambda: Unit(expression=1 / sympy.Symbol('day'))
    gram_units = lambda: Unit(expression=sympy.Symbol('gram'))
    per_day_per_person_units = lambda: Unit(expression=1 / (sympy.Symbol('day') * sympy.Symbol('person')))

    # See Table 1 of the paper
    c = {
        'S': Concept(name='S', units=person_units(), identifiers={'ido': '0000514'}),
        'E': Concept(name='E', units=person_units(), identifiers={'apollosv': '0000154'}),
        'I': Concept(name='I', units=person_units(), identifiers={'ido': '0000511'}),
        'V': Concept(name='V', units=virus_units(), identifiers={'vido': '0001331'}),
    }

    parameters = {
        'gamma': Parameter(name='gamma', value=None, units=per_day_units()),
        'delta': Parameter(name='delta', value=1 / 8, units=per_day_units()),
        'alpha': Parameter(name='alpha', value=500, units=gram_units(),
                           distribution=Distribution(type='Uniform1',
                                                     parameters={
                                                         'minimum': 51,
                                                         'maximum': 796
                                                     })),
        'lambda': Parameter(name='lambda', value=None, units=per_day_per_person_units()),
        'beta': Parameter(name='beta', value=None, units=virus_per_gram_units()),
        'k': Parameter(name='k', value=1 / 3, units=per_day_units()),
    }

    initials = {
        'S': Initial(concept=Concept(name='S'), value=2_300_000),
        'E': Initial(concept=Concept(name='E'), value=1000),
        'I': Initial(concept=Concept(name='I'), value=0),
        'V': Initial(concept=Concept(name='V'), value=0),
    }

    S, E, I, V, gamma, delta, alpha, lmbd, beta, k = \
        sympy.symbols('S E I V gamma delta alpha lambda beta k')

    t1 = ControlledConversion(subject=c['S'],
                              outcome=c['E'],
                              controller=c['I'],
                              rate_law=S * I * lmbd)
    t2 = NaturalConversion(subject=c['E'],
                           outcome=c['I'],
                           rate_law=k * E)
    t3 = NaturalDegradation(subject=c['I'],
                            rate_law=delta * I)
    t4 = ControlledProduction(outcome=c['V'],
                              controller=c['I'],
                              rate_law=alpha * beta * (1 - gamma) * I)
    templates = [t1, t2, t3, t4]
    observables = {}
    tm = TemplateModel(
        templates=templates,
        parameters=parameters,
        initials=initials,
        time=Time(name='t', units=day_units()),
        observables=observables,
        annotations=Annotations(name='Scenario 3 base model')
    )
    AskeNetPetriNetModel(Model(tm)).to_json_file('deg_prod_test.json')
    from mira.sources.askenet.petrinet import model_from_json_file
    tm2 = model_from_json_file('deg_prod_test.json')

    for t1, t2 in zip(tm.templates, tm2.templates):
        assert t1.type == t2.type