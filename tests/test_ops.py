"""Tests for operations on template models."""

import unittest
from collections import Counter
from copy import deepcopy as _d
from fractions import Fraction

import sympy

from mira.metamodel import *
from mira.metamodel.ops import stratify, simplify_rate_law, \
    counts_to_dimensionless, add_observable_pattern, \
    get_observable_for_concepts, check_simplify_rate_laws
from mira.examples.sir import cities, sir, sir_2_city, sir_parameterized
from mira.examples.concepts import infected, susceptible
from mira.examples.chime import sviivr


def _s(s):
    return sympy.Symbol(s)


class TestOperations(unittest.TestCase):
    """A test case for operations on template models."""

    def test_stratify_full(self):
        """Test stratifying a template model by labels."""
        infection = ControlledConversion(
            subject=_d(susceptible),
            outcome=_d(infected),
            controller=_d(infected),
            rate_law=safe_parse_expr(
                'beta * susceptible_population * infected_population',
                local_dict={'beta': sympy.Symbol('beta')}
            )
        )
        self.assertEqual(
            {"susceptible_population", "infected_population"},
            infection.get_concept_names(),
        )
        self.assertEqual(
            sympy.Symbol("beta"),
            infection.get_mass_action_symbol(),
            msg=f"Could not find mass action symbol in rate law: {infection.rate_law}",
        )

        expected_0 = ControlledConversion(
            name="t_unvaccinated_unvaccinated",
            subject=susceptible.with_context(vaccination_status="unvaccinated",
                                             do_rename=True),
            outcome=infected.with_context(vaccination_status="unvaccinated",
                                          do_rename=True),
            controller=infected.with_context(vaccination_status="unvaccinated",
                                             do_rename=True),
            rate_law=safe_parse_expr(
                'beta_0_0 * susceptible_population_unvaccinated * infected_population_unvaccinated',
                local_dict={'beta_0_0': sympy.Symbol('beta_0_0')}
            )
        )
        expected_1 = ControlledConversion(
            name="t_unvaccinated_vaccinated",
            subject=susceptible.with_context(vaccination_status="unvaccinated",
                                             do_rename=True),
            outcome=infected.with_context(vaccination_status="unvaccinated",
                                          do_rename=True),
            controller=infected.with_context(vaccination_status="vaccinated",
                                             do_rename=True),
            rate_law=safe_parse_expr(
                'beta_0_1 * susceptible_population_unvaccinated * infected_population_vaccinated',
                local_dict={'beta_0_1': sympy.Symbol('beta_0_1')}
            )
        )
        expected_2 = ControlledConversion(
            name="t_vaccinated_unvaccinated",
            subject=susceptible.with_context(vaccination_status="vaccinated",
                                             do_rename=True),
            outcome=infected.with_context(vaccination_status="vaccinated",
                                          do_rename=True),
            controller=infected.with_context(vaccination_status="unvaccinated",
                                             do_rename=True),
            rate_law=safe_parse_expr(
                'beta_1_0 * susceptible_population_vaccinated * infected_population_unvaccinated',
                local_dict={'beta_1_0': sympy.Symbol('beta_1_0')}
            )
        )
        expected_3 = ControlledConversion(
            name="t_vaccinated_vaccinated",
            subject=susceptible.with_context(vaccination_status="vaccinated",
                                             do_rename=True),
            outcome=infected.with_context(vaccination_status="vaccinated",
                                          do_rename=True),
            controller=infected.with_context(vaccination_status="vaccinated",
                                             do_rename=True),
            rate_law=safe_parse_expr(
                'beta_1_1 * susceptible_population_vaccinated * infected_population_vaccinated',
                local_dict={'beta_1_1': sympy.Symbol('beta_1_1')}
            )
        )

        tm = TemplateModel(
            templates=[infection],
            parameters={
                "beta": Parameter(name="beta", value=0.1),
            },
            initials={
                susceptible.name: Initial(concept=susceptible, expression=sympy.Float('5.0')),
                infected.name: Initial(concept=infected, expression=sympy.Float('7.0')),
            }
        )
        tm_stratified = TemplateModel(
            templates=[expected_0, expected_1, expected_2, expected_3],
            parameters={
                "beta_0_0": Parameter(name="beta_0_0", value=0.1),
                "beta_1_0": Parameter(name="beta_1_0", value=0.1),
                "beta_1_1": Parameter(name="beta_1_1", value=0.1),
                "beta_0_1": Parameter(name="beta_0_1", value=0.1),
            },
            initials={
                f"{susceptible.name}_vaccinated": Initial(
                    concept=susceptible.with_context(vaccination_status="vaccinated",
                                                     do_rename=True), expression=sympy.Float('2.5'),
                ),
                f"{susceptible.name}_unvaccinated": Initial(
                    concept=susceptible.with_context(vaccination_status="unvaccinated",
                                                     do_rename=True), expression=sympy.Float('2.5'),
                ),
                f"{infected.name}_vaccinated": Initial(
                    concept=infected.with_context(vaccination_status="vaccinated",
                                                  do_rename=True), expression=sympy.Float('3.5'),
                ),
                f"{infected.name}_unvaccinated": Initial(
                    concept=infected.with_context(vaccination_status="unvaccinated",
                                                  do_rename=True), expression=sympy.Float('3.5'),
                ),
            }
        )

        actual = stratify(
            tm, key="vaccination_status",
            strata=["unvaccinated", "vaccinated"],
            cartesian_control=True,
            structure=[],
            modify_names=True,
        )
        self.assertEqual(4, len(actual.templates))
        self.assertEqual(
            {"beta_0_0": 0.1, "beta_0_1": 0.1, "beta_1_0": 0.1, "beta_1_1": 0.1},
            {k: p.value for k, p in actual.parameters.items()}
        )
        self.assertEqual(
            {
                f"{susceptible.name}_vaccinated": SympyExprStr(2.5),
                f"{susceptible.name}_unvaccinated": SympyExprStr(2.5),
                f"{infected.name}_vaccinated": SympyExprStr(3.5),
                f"{infected.name}_unvaccinated": SympyExprStr(3.5),
            },
            {k: i.expression for k, i in actual.initials.items()}
        )
        self.assertEqual(tm_stratified.parameters, actual.parameters)
        self.assertTrue(actual.initials['infected_population_vaccinated'].expression.equals(
            tm_stratified.initials['infected_population_vaccinated'].expression))

        def one_to_one_concept_mapping(strat_concepts, actual_concepts):
            matched_concept_idxs = set()
            for strat_concept in strat_concepts:
                matched = False
                for concept_idx, actual_concept in enumerate(actual_concepts):
                    if (strat_concept.is_equal_to(actual_concept) and
                        concept_idx not in matched_concept_idxs):
                            matched_concept_idxs.add(concept_idx)
                            matched = True
                            break
                if not matched:
                    return False
            return True

        self.assertTrue(one_to_one_concept_mapping(
            [t.subject for t in tm_stratified.templates],
            [t.subject for t in actual.templates]))

        self.assertTrue(one_to_one_concept_mapping(
            [t.outcome for t in tm_stratified.templates],
            [t.outcome for t in actual.templates]))

        self.assertTrue(one_to_one_concept_mapping(
            [t.controller for t in tm_stratified.templates],
            [t.controller for t in actual.templates]))


    def test_stratify(self):
        """Test stratifying a template model by labels."""
        actual = stratify(sir_parameterized, key="city", strata=cities, cartesian_control=False, directed=False)
        for template in actual.templates:
            for concept in template.get_concepts():
                self.assertIn("city", concept.context)
        self.assert_unique_controllers(actual)
        self.assertEqual(
            {template.get_key() for template in sir_2_city.templates},
            {template.get_key() for template in actual.templates},
        )

        original_name = "susceptible_population"
        self.assertIn(original_name, sir_parameterized.initials)
        for city in cities:
            key = f"{original_name}_{city}".replace(':', '_')
            self.assertIn(key, actual.initials, msg="")
            # Cannot use .args[0] here as .args[0] not a primitive data type
            self.assertEqual(
                float(SympyExprStr(float(sir_parameterized.initials[original_name].expression.__str__()) / len(cities)).__str__()),
                float(Fraction(actual.initials[key].expression.__str__())),
                msg=f"initial value was not copied from original compartment "
                    f"({original_name}) to stratified compartment ({key})"
            )

    def test_stratify_w_name_map(self):
        """Test stratifying a template model by labels."""
        city_name_map = {
            "geonames:5128581": "New York City", "geonames:4930956": "Boston"
        }
        actual = stratify(
            sir_parameterized,
            key="city",
            strata=cities,
            strata_curie_to_name=city_name_map,
            cartesian_control=False,
            directed=False
        )
        for template in actual.templates:
            for concept in template.get_concepts():
                self.assertIn("city", concept.context)
        self.assert_unique_controllers(actual)
        self.assertEqual(
            {template.get_key() for template in sir_2_city.templates},
            {template.get_key() for template in actual.templates},
        )

        original_name = "susceptible_population"
        self.assertIn(original_name, sir_parameterized.initials)
        for city_curie in cities:
            city_name = city_name_map.get(city_curie, city_curie)
            key = f"{original_name}_{city_name}".replace(':', '_')
            self.assertIn(key, actual.initials, msg=f"Key '{key}' not in initials")
            # Cannot use .args[0] here as .args[0] not a primitive data type
            self.assertEqual(
                float(SympyExprStr(float(sir_parameterized.initials[original_name].expression.__str__()) / len(cities)).__str__()),
                float(Fraction(actual.initials[key].expression.__str__())),
                msg=f"initial value was not copied from original compartment "
                    f"({original_name}) to stratified compartment ({key})"
            )

    def test_stratify_w_client_mapping(self):
        """Test stratifying a template model by labels."""
        city_name_map = {
            "geonames:5128581": "New York City", "geonames:4930956": "Boston"
        }
        actual = stratify(
            sir_parameterized,
            key="city",
            strata=cities,
            strata_name_lookup=True,
            cartesian_control=False,
            directed=False
        )
        for template in actual.templates:
            for concept in template.get_concepts():
                self.assertIn("city", concept.context)
        self.assert_unique_controllers(actual)
        self.assertEqual(
            {template.get_key() for template in sir_2_city.templates},
            {template.get_key() for template in actual.templates},
        )

        original_name = "susceptible_population"
        self.assertIn(original_name, sir_parameterized.initials)
        for city in cities:
            city_name = city_name_map.get(city, city)
            key = f"{original_name}_{city_name}".replace(':', '_')
            self.assertIn(key, actual.initials, msg=f"Key '{key}' not in initials")
            # Cannot use .args[0] here as .args[0] not a primitive data type
            self.assertEqual(
                float(SympyExprStr(float(sir_parameterized.initials[original_name].expression.__str__()) / len(cities)).__str__()),
                float(Fraction(actual.initials[key].expression.__str__())),
                msg=f"initial value was not copied from original compartment "
                    f"({original_name}) to stratified compartment ({key})"
            )

    @unittest.skip(reason="Small bookkeeping still necessary")
    def test_stratify_control(self):
        """Test stratifying a template that properly multiples the controllers."""
        actual = stratify(
            sir,
            key="vaccination_status",
            strata={"vaccinated", "unvaccinated"},
            structure=[],  # i.e., don't add any conversions
            cartesian_control=True,  # i.e., cross-product control based on strata
        )
        for template in actual.templates:
            for concept in template.get_concepts():
                self.assertIn("vaccination_status", concept.context)
        self.assert_unique_controllers(actual)
        self.assertEqual(
            {template.get_key(): template for template in sviivr.templates},
            {template.get_key(): template for template in actual.templates},
        )

    def test_stratify_directed_simple(self):
        stratified_sir = stratify(sir_parameterized,
                                  key="vaccination_status",
                                  strata=["unvaccinated", "vaccinated"],
                                  directed=True,
                                  cartesian_control=True,
                                  modify_names=True)
        # One way transition unvaccinated to vaccinated == 3
        # 4x controlled conversion of susceptible to infected
        # 2x natural conversion of infected to recovered
        self.assertEqual(9, len(stratified_sir.templates))

        # check that conversion does not go from vaccinated to unvaccinated
        for template in stratified_sir.templates:
            # Should not have any vaccinated to unvaccinated conversions
            if template.outcome.name.endswith("_unvaccinated"):
                vaccinated_name = template.outcome.name.replace(
                    "_unvaccinated", "_vaccinated")
                self.assertFalse(template.subject.name == vaccinated_name)

    def assert_unique_controllers(self, tm: TemplateModel):
        """Assert that controllers are unique."""
        for template in tm.templates:
            if not isinstance(template, (GroupedControlledConversion,
                                         GroupedControlledProduction)):
                continue
            counter = Counter(
                controller.get_key()
                for controller in template.controllers
            )
            duplicates = {
                key
                for key, count in counter.most_common()
                if count > 1
            }
            self.assertEqual(set(), duplicates)

    def test_simplify_rate_law(self):
        parameters = ['alpha', 'beta', 'gamma', 'delta']
        controllers = [
            Concept(name='Ailing'),
            Concept(name='Diagnosed'),
            Concept(name='Infected'),
            Concept(name='Recognized')
        ]
        rate_law = safe_parse_expr('1.0*Susceptible*(Ailing*gamma + '
                                   'Diagnosed*beta + Infected*alpha + '
                                   'Recognized*delta)',
                                   local_dict={p: _s(p) for p in parameters})
        template = GroupedControlledConversion(
            name='t1',
            controllers=controllers,
            subject=Concept(name='Susceptible'),
            outcome=Concept(name='Infected'),
            rate_law=rate_law
        )
        simplified_templates = simplify_rate_law(template, parameters)
        assert len(simplified_templates) == 4, simplified_templates
        assert all(isinstance(t, ControlledConversion)
                   for t in simplified_templates)
        assert all(t.name is not None for t in simplified_templates)
        assert len({t.name for t in simplified_templates}) \
            == len(simplified_templates)

        template = GroupedControlledDegradation(
            name='t1',
            controllers=controllers,
            subject=Concept(name='Susceptible'),
            rate_law=rate_law
        )
        simplified_templates = simplify_rate_law(template, parameters)
        assert len(simplified_templates) == 4, simplified_templates
        assert all(isinstance(t, ControlledDegradation)
                   for t in simplified_templates)
        assert all(t.name is not None for t in simplified_templates)
        assert len({t.name for t in simplified_templates}) \
               == len(simplified_templates)

    def test_simplify_rate_law2(self):
        def _make_template(rate_law):
            template = GroupedControlledConversion(
                rate_law=rate_law,
                controllers=[Concept(name='A'),
                             Concept(name='B')],
                subject=Concept(name='S'),
                outcome=Concept(name='O'))
            return template

        # This one cannot be simplified
        rate_law = (_s('alpha') * _s('S') * _s('A')) / _s('B')
        template = _make_template(rate_law)
        templates = simplify_rate_law(template,
                                      {'alpha': Parameter(name='alpha',
                                                          value=1.0)})
        assert len(templates) == 1, templates
        assert templates[0].type == 'GroupedControlledConversion'

        # This one can be simplified
        rate_law = (1 - _s('alpha')) * _s('S') * (_s('A') + _s('B'))
        template = _make_template(rate_law)
        templates = simplify_rate_law(template,
                                      {'alpha': Parameter(name='alpha',
                                                          value=1.0)})
        assert len(templates) == 2, templates
        assert all(t.type == 'ControlledConversion' for t in templates)

        # This one can be simplified too
        rate_law = (1 - _s('alpha')) * _s('S') * (_s('A') + _s('beta') * _s('B'))
        template = _make_template(rate_law)
        templates = simplify_rate_law(template,
                                      {'alpha': Parameter(name='alpha',
                                                          value=1.0),
                                       'beta': Parameter(name='beta',
                                                         value=2.0)})
        assert len(templates) == 2, templates
        assert all(t.type == 'ControlledConversion' for t in templates)
        assert templates[0].rate_law.args[0].equals(
            (1 - _s('alpha')) * _s('S') * _s('A'))
        assert templates[1].rate_law.args[0].equals(
            (1 - _s('alpha')) * _s('beta') * _s('S') * _s('B'))


def test_counts_to_dimensionless():
    """Test that counts are converted to dimensionless."""
    from mira.metamodel import Unit
    tm = _d(sir_parameterized)

    for template in tm.templates:
        for concept in template.get_concepts():
            concept.units = Unit(expression=sympy.Symbol('person'))
    tm.initials['susceptible_population'].expression = SympyExprStr(1e5 - 1)
    tm.initials['infected_population'].expression = SympyExprStr(1)
    tm.initials['immune_population'].expression = SympyExprStr(0)

    tm.parameters['beta'].units = \
        Unit(expression=1 / (sympy.Symbol('person') * sympy.Symbol('day')))
    old_beta = tm.parameters['beta'].value

    for initial in tm.initials.values():
        initial.concept.units = Unit(expression=sympy.Symbol('person'))

    tm = counts_to_dimensionless(tm, 'person', 1e5)
    for template in tm.templates:
        for concept in template.get_concepts():
            assert concept.units.expression.args[0].equals(1), concept.units

    assert tm.parameters['beta'].units.expression.args[0].equals(1 / sympy.Symbol('day'))
    assert tm.parameters['beta'].value == old_beta * 1e5

    assert SympyExprStr((1e5 - 1) / 1e5).equals(tm.initials['susceptible_population'].expression)
    assert SympyExprStr(1 / 1e5).equals(tm.initials['infected_population'].expression)
    assert SympyExprStr(0).equals(tm.initials['immune_population'].expression)

    for initial in tm.initials.values():
        assert initial.concept.units.expression.args[0].equals(1)


def test_stratify_observable():
    tm = _d(sir_parameterized)
    symbols = set(tm.get_concepts_name_map().keys())
    expr = sympy.Add(*[sympy.Symbol(s) for s in symbols])
    tm.observables = {'half_population': Observable(
        name='half_population',
        expression=SympyExprStr(expr / 2))
    }
    tm = stratify(tm,
                  key='age',
                  strata=['y', 'o'],
                  structure=[],
                  cartesian_control=True)
    print(tm.observables['half_population'].expression.args[0])


def test_stratify_initials():
    person_units = lambda: Unit(expression=sympy.Symbol('person'))
    day_units = lambda: Unit(expression=sympy.Symbol('day'))
    per_day_units = lambda: Unit(expression=1 / sympy.Symbol('day'))
    dimensionless_units = lambda: Unit(expression=sympy.Integer('1'))

    c = {
        'S': Concept(name='S', units=person_units(), identifiers={'ido': '0000514'}),
        'E': Concept(name='E', units=person_units(), identifiers={'apollosv': '0000154'}),
        'I': Concept(name='I', units=person_units(), identifiers={'ido': '0000511'}),
        'R': Concept(name='R', units=person_units(), identifiers={'ido': '0000592'}),
        'D': Concept(name='D', units=person_units(), identifiers={'ncit': 'C28554'}),
    }

    parameters = {
        'gamma': Parameter(name='gamma', value=1 / 11, units=per_day_units()),
        'delta': Parameter(name='delta', value=1 / 5, units=per_day_units()),
        'alpha': Parameter(name='alpha', value=0.000064, units=dimensionless_units()),
        'rho': Parameter(name='rho', value=1 / 9, units=per_day_units()),
        'N': Parameter(name='N', value=5_600_000, units=person_units()),
        'beta_s': Parameter(name='beta_s', value=1, units=per_day_units()),
        'beta_c': Parameter(name='beta_c', value=0.4, units=per_day_units()),
        't_0': Parameter(name='t_0', value=89, unts=day_units, units=day_units()),
        # D=11, gamma = 1/D, R_0 = 5 and
        # beta = R_0 * gamma * mask(t) so kappa = 5/11
        'kappa': Parameter(name='kappa', value=5 / 11, units=per_day_units()),
        'k': Parameter(name='k', value=5.0, units=dimensionless_units()),
    }

    initials = {
        'S': Initial(concept=Concept(name='S'), expression=sympy.Integer(str(5600000 - 1))),
        'E': Initial(concept=Concept(name='E'), expression=sympy.Integer('1')),
        'I': Initial(concept=Concept(name='I'), expression=sympy.Integer('0')),
        'R': Initial(concept=Concept(name='R'), expression=sympy.Integer('0')),
        'D': Initial(concept=Concept(name='D'), expression=sympy.Integer('0')),
    }

    S, E, I, R, D, N, kappa, beta_s, beta_c, k, t_0, t, alpha, delta, rho, gamma = \
        sympy.symbols('S E I R D N kappa beta_s beta_c k t_0 t alpha delta rho gamma')

    observables = {
        'infected': Observable(name='infected', expression=SympyExprStr(I))
    }

    m_1 = (beta_s - beta_c) / (1 + sympy.exp(-k * (t_0 - t))) + beta_c
    beta = kappa * m_1

    t1 = ControlledConversion(subject=c['S'],
                              outcome=c['E'],
                              controller=c['I'],
                              rate_law=S * I * beta / N)
    t2 = NaturalConversion(subject=c['E'],
                           outcome=c['I'],
                           rate_law=delta * E)
    t3 = NaturalConversion(subject=c['I'],
                           outcome=c['R'],
                           rate_law=(1 - alpha) * gamma * I)
    t4 = NaturalConversion(subject=c['I'],
                           outcome=c['D'],
                           rate_law=alpha * rho * I)
    templates = [t1, t2, t3, t4]
    tm = TemplateModel(
        templates=templates,
        parameters=parameters,
        initials=initials,
        time=Time(name='t', units=day_units()),
        observables=observables,
        annotations=Annotations(name='Scenario 1a')
    )

    tm_age = stratify(tm,
                      key='age',
                      strata=['young', 'middle_aged', 'old'],
                      structure=[],
                      cartesian_control=True,
                      params_to_stratify={'beta'})
    nconcept = len(tm_age.get_concepts_map())
    print(nconcept)
    assert len(tm_age.initials) == nconcept

    tm_diag = stratify(tm_age,
                       key='diagnosis',
                       strata=['undiagnosed', 'diagnosed'],
                       structure=[['undiagnosed', 'diagnosed']],
                       directed=True,
                       concepts_to_stratify={'I_young', 'I_middle_aged', 'I_old'},
                       params_to_stratify={('kappa_%d' % i) for i in range(3)},
                       cartesian_control=False)
    assert tm_diag.templates

    nconcept = len(tm_diag.get_concepts_map())
    assert nconcept
    print(nconcept)
    assert len(tm_diag.initials) == nconcept


def test_deactivate():
    from mira.examples.sir import sir_parameterized
    tm = _d(sir_parameterized)

    def condition(template):
        if isinstance(template, NaturalConversion) and \
                template.subject.name == 'I':
            return False
        return True

    deactivate_templates(tm, condition)

    assert len(tm.templates) == 2
    assert tm.templates[1].rate_law.args[0] == sympy.core.numbers.Zero()


def test_stratify_excluded_species():
    from mira.examples.sir import sir_parameterized

    tm = stratify(sir_parameterized,
                  key='vax',
                  strata=['vax', 'unvax'],
                  structure=[],
                  cartesian_control=True,
                  concepts_to_stratify=['susceptible_population'])

    assert len(tm.templates) == 3, templates
    assert tm.templates[0].subject.name == 'susceptible_population_vax'
    assert tm.templates[0].outcome.name == 'infected_population'
    assert tm.templates[0].controller.name == 'infected_population'
    assert tm.templates[1].subject.name == 'susceptible_population_unvax'
    assert tm.templates[1].outcome.name == 'infected_population'
    assert tm.templates[1].controller.name == 'infected_population'


def test_stratify_parameter_consistency():
    templates = [
        NaturalDegradation(subject=Concept(name='A'),
                           rate_law=sympy.Symbol('alpha') * sympy.Symbol('A')),
        NaturalDegradation(subject=Concept(name='A'),
                           rate_law=sympy.Symbol('alpha') * sympy.Symbol('A')),
        NaturalDegradation(subject=Concept(name='B'),
                           rate_law=sympy.Symbol('alpha') * sympy.Symbol('B')),
    ]
    tm = TemplateModel(templates=templates,
                       parameters={'alpha': Parameter(name='alpha', value=0.1)})
    tm = stratify(tm, key='age', strata=['young', 'old'], structure=[])
    # This should be two (alpha_0 and alpha_1 instead of 6 which used to
    # be the case when parameters would be incrementally numbered for each
    # new template
    assert len(tm.parameters) == 2


def test_get_observable_for_concepts():
    concepts = [
        Concept(name='A'),
        Concept(name='B'),
        Concept(name='C'),
    ]
    obs = get_observable_for_concepts(concepts, 'obs')
    assert obs.name == 'obs'
    assert obs.expression.args[0] == sum([sympy.Symbol(c.name) for c in concepts])


def test_add_observable_pattern():
    templates = [
        NaturalDegradation(subject=Concept(name='A', identifiers={'ido': '0000514'}),
                           rate_law=sympy.Symbol('alpha') * sympy.Symbol('A')),
        NaturalDegradation(subject=Concept(name='B', identifiers={'ido': '0000515'}),
                           rate_law=sympy.Symbol('alpha') * sympy.Symbol('B')),
    ]
    tm = TemplateModel(templates=templates,
                       parameters={'alpha': Parameter(name='alpha', value=0.1)})
    tm = stratify(tm, key='age', strata=['young', 'old'], structure=[])
    add_observable_pattern(tm, name='A', identifiers={'ido': '0000514'})
    assert 'A' in tm.observables
    obs = tm.observables['A']
    assert obs.expression.args[0] == sympy.Symbol('A_old') + sympy.Symbol('A_young')

    add_observable_pattern(tm, 'young', context={'age': 'young'})
    assert 'young' in tm.observables
    obs = tm.observables['young']
    assert obs.expression.args[0] == sympy.Symbol('A_young') + sympy.Symbol('B_young')


def test_stratify_initials_parameters():
    s = Concept(name='S')
    t = NaturalDegradation(subject=s, rate_law=sympy.Symbol('alpha') *
                                               sympy.Symbol(s.name))
    S0 = Initial(concept=s, expression=sympy.Symbol('S0'))
    tm = TemplateModel(templates=[t],
                       parameters={'alpha': Parameter(name='alpha', value=0.1),
                                   'S0': Parameter(name='S0', value=1000)},
                       initials={'S': S0})
    tm1 = stratify(tm, key='age', strata=['young', 'old'], structure=[],
                   param_renaming_uses_strata_names=True)
    assert 'S_young' in tm1.initials
    assert tm1.initials['S_young'].expression.args[0] == sympy.Symbol('S0_young')
    assert 'S_old' in tm1.initials
    assert tm1.initials['S_old'].expression.args[0] == sympy.Symbol('S0_old')
    assert 'S0_young' in tm1.parameters
    assert tm1.parameters['S0_young'].value == 500
    assert 'S0_old' in tm1.parameters
    assert tm1.parameters['S0_old'].value == 500

    tm2 = stratify(tm, key='age', strata=['young', 'old'], structure=[],
                   param_renaming_uses_strata_names=True,
                   params_to_preserve={'S0'})
    assert 'S_young' in tm2.initials
    assert tm2.initials['S_young'].expression.args[0] == sympy.Symbol('S0') / 2
    assert 'S_old' in tm2.initials
    assert tm2.initials['S_old'].expression.args[0] == sympy.Symbol('S0') / 2
    assert 'S0' in tm2.parameters
    assert tm2.parameters['S0'].value == 1000

    tm3 = stratify(tm, key='age', strata=['young', 'old'], structure=[],
                   param_renaming_uses_strata_names=True,
                   concepts_to_preserve={'S'})
    assert set(tm3.initials) == {'S'}
    assert tm3.initials['S'].expression.args[0] == \
        sympy.Symbol('S0_old') + sympy.Symbol('S0_young')
    assert set(tm3.parameters) == {'alpha', 'S0_old', 'S0_young'}
    assert tm3.parameters['S0_old'].value == 500
    assert tm3.parameters['S0_young'].value == 500


def test_check_simplify():
    a, b, c, A, B, C = sympy.symbols('a b c A B C')
    template = GroupedControlledDegradation(
        subject=Concept(name='A'),
        controllers=[Concept(name='B'), Concept(name='C')],
        rate_law=SympyExprStr((b * B + c * C) * A),
    )
    parameters = {'a': Parameter(name='a', value=1),
                  'b': Parameter(name='b', value=1),
                  'c': Parameter(name='c', value=1)}
    tm = TemplateModel(templates=[template],
                       parameters=parameters)
    res = check_simplify_rate_laws(tm)
    assert res['result'] == 'MEANINGFUL_CHANGE'
    assert res['max_controller_decrease'] == 1