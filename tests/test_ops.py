"""Tests for operations on template models."""
import itertools
import unittest
from collections import Counter
from copy import deepcopy as _d

import sympy

from mira.metamodel import *
from mira.metamodel.ops import stratify, simplify_rate_law, counts_to_dimensionless
from mira.examples.sir import cities, sir, sir_2_city, sir_parameterized
from mira.examples.concepts import infected, susceptible
from mira.examples.chime import sviivr
from mira.modeling.viz import GraphicalModel


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
            subject=susceptible.with_context(vaccination_status="unvaccinated",
                                             do_rename=True),
            outcome=infected.with_context(vaccination_status="unvaccinated",
                                          do_rename=True),
            controller=infected.with_context(vaccination_status="unvaccinated",
                                             do_rename=True),
            rate_law=safe_parse_expr(
                'beta_0 * susceptible_population_unvaccinated * infected_population_unvaccinated',
                local_dict={'beta_0': sympy.Symbol('beta_0')}
            )
        )
        expected_1 = ControlledConversion(
            subject=susceptible.with_context(vaccination_status="unvaccinated",
                                             do_rename=True),
            outcome=infected.with_context(vaccination_status="unvaccinated",
                                          do_rename=True),
            controller=infected.with_context(vaccination_status="vaccinated",
                                             do_rename=True),
            rate_law=safe_parse_expr(
                'beta_1 * susceptible_population_unvaccinated * infected_population_vaccinated',
                local_dict={'beta_1': sympy.Symbol('beta_1')}
            )
        )
        expected_2 = ControlledConversion(
            subject=susceptible.with_context(vaccination_status="vaccinated",
                                             do_rename=True),
            outcome=infected.with_context(vaccination_status="vaccinated",
                                          do_rename=True),
            controller=infected.with_context(vaccination_status="vaccinated",
                                             do_rename=True),
            rate_law=safe_parse_expr(
                'beta_2 * susceptible_population_vaccinated * infected_population_vaccinated',
                local_dict={'beta_2': sympy.Symbol('beta_2')}
            )
        )
        expected_3 = ControlledConversion(
            subject=susceptible.with_context(vaccination_status="vaccinated",
                                             do_rename=True),
            outcome=infected.with_context(vaccination_status="vaccinated",
                                          do_rename=True),
            controller=infected.with_context(vaccination_status="unvaccinated",
                                             do_rename=True),
            rate_law=safe_parse_expr(
                'beta_3 * susceptible_population_vaccinated * infected_population_unvaccinated',
                local_dict={'beta_3': sympy.Symbol('beta_3')}
            )
        )

        tm = TemplateModel(
            templates=[infection],
            parameters={
                "beta": Parameter(name="beta", value=0.1),
            },
            initials={
                susceptible.name: Initial(concept=susceptible, value=5.0),
                infected.name: Initial(concept=infected, value=7.0),
            }
        )
        tm_stratified = TemplateModel(
            templates=[expected_0, expected_1, expected_2, expected_3],
            parameters={
                "beta_0": Parameter(name="beta_0", value=0.1),
                "beta_1": Parameter(name="beta_1", value=0.1),
                "beta_2": Parameter(name="beta_2", value=0.1),
                "beta_3": Parameter(name="beta_3", value=0.1),
            },
            initials={
                f"{susceptible.name}_vaccinated": Initial(
                    concept=susceptible.with_context(vaccination_status="vaccinated",
                                                     do_rename=True), value=2.5,
                ),
                f"{susceptible.name}_unvaccinated": Initial(
                    concept=susceptible.with_context(vaccination_status="unvaccinated",
                                                     do_rename=True), value=2.5,
                ),
                f"{infected.name}_vaccinated": Initial(
                    concept=infected.with_context(vaccination_status="vaccinated",
                                                  do_rename=True), value=3.5,
                ),
                f"{infected.name}_unvaccinated": Initial(
                    concept=infected.with_context(vaccination_status="unvaccinated",
                                                  do_rename=True), value=3.5,
                ),
            }
        )

        actual = stratify(
            tm, key="vaccination_status",
            strata=["vaccinated", "unvaccinated"],
            cartesian_control=True,
            structure=[],
            modify_names=True,
        )
        self.assertEqual(4, len(actual.templates))
        self.assertEqual(
            {"beta_0": 0.1, "beta_1": 0.1, "beta_2": 0.1, "beta_3": 0.1},
            {k: p.value for k, p in actual.parameters.items()}
        )
        self.assertEqual(
            {
                f"{susceptible.name}_vaccinated": 2.5,
                f"{susceptible.name}_unvaccinated": 2.5,
                f"{infected.name}_vaccinated": 3.5,
                f"{infected.name}_unvaccinated": 3.5,
            },
            {k: i.value for k, i in actual.initials.items()}
        )
        self.assertEqual(tm_stratified.parameters, actual.parameters)
        self.assertEqual(tm_stratified.initials, actual.initials)
        self.assertEqual(
            [t.subject for t in tm_stratified.templates],
            [t.subject for t in actual.templates],
        )
        self.assertEqual(
            [t.outcome for t in tm_stratified.templates],
            [t.outcome for t in actual.templates],
        )
        self.assertEqual(
            [t.controller for t in tm_stratified.templates],
            [t.controller for t in actual.templates],
        )
        self.assertEqual(tm_stratified.templates, actual.templates)

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
            self.assertEqual(
                sir_parameterized.initials[original_name].value / len(cities),
                actual.initials[key].value,
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
            if not isinstance(
                template,
                (GroupedControlledConversion, GroupedControlledProduction)
            ):
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
        template = GroupedControlledConversion(
            controllers=[
                Concept(name='Ailing'),
                Concept(name='Diagnosed'),
                Concept(name='Infected'),
                Concept(name='Recognized')
            ],
            subject=Concept(name='Susceptible'),
            outcome=Concept(name='Infected'),
            rate_law=safe_parse_expr('1.0*Susceptible*(Ailing*gamma + '
                                     'Diagnosed*beta + Infected*alpha + '
                                     'Recognized*delta)',
                                     local_dict={p: _s(p) for p in parameters})
        )
        simplified_templates = \
            simplify_rate_law(template, parameters)
        assert len(simplified_templates) == 4, simplified_templates
        assert all(isinstance(t, ControlledConversion)
                   for t in simplified_templates)

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
        rate_law = (1 - _s('alpha')) * _s('S') * (_s('A') + _s('beta')*_s('B'))
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
    tm.initials['susceptible_population'].value = 1e5-1
    tm.initials['infected_population'].value = 1
    tm.initials['immune_population'].value = 0

    tm.parameters['beta'].units = \
        Unit(expression=1/(sympy.Symbol('person')*sympy.Symbol('day')))
    old_beta = tm.parameters['beta'].value

    for initial in tm.initials.values():
        initial.concept.units = Unit(expression=sympy.Symbol('person'))

    tm = counts_to_dimensionless(tm, 'person', 1e5)
    for template in tm.templates:
        for concept in template.get_concepts():
            assert concept.units.expression.args[0].equals(1), concept.units

    assert tm.parameters['beta'].units.expression.args[0].equals(1/sympy.Symbol('day'))
    assert tm.parameters['beta'].value == old_beta*1e5

    assert tm.initials['susceptible_population'].value == (1e5-1)/1e5
    assert tm.initials['infected_population'].value == 1/1e5
    assert tm.initials['immune_population'].value == 0

    for initial in tm.initials.values():
        assert initial.concept.units.expression.args[0].equals(1)


def test_stratify_observable():
    tm = _d(sir_parameterized)
    symbols = set(tm.get_concepts_name_map().keys())
    expr = sympy.Add(*[sympy.Symbol(s) for s in symbols])
    tm.observables = {'half_population': Observable(
        name='half_population',
        expression=SympyExprStr(expr/2))
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
        'S': Initial(concept=Concept(name='S'), value=5_600_000 - 1),
        'E': Initial(concept=Concept(name='E'), value=1),
        'I': Initial(concept=Concept(name='I'), value=0),
        'R': Initial(concept=Concept(name='R'), value=0),
        'D': Initial(concept=Concept(name='D'), value=0),
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


def test_partial_stratify():
    # Test that we can stratify a model with a subset of concepts
    # and parameters
    tm = _d(sir_parameterized)
    tm_strat = stratify(tm,
                        key='age',
                        strata=['young', 'old'],
                        structure=[],
                        cartesian_control=True,
                        params_to_preserve={'beta'})

    # We should have 6 concepts (S_young, S_old, I_young, I_old, R_young, R_old)
    # and 3 parameters (gamma_young, gamma_old, beta)
    assert len(tm_strat.get_concepts_map()) == 6
    assert len(tm_strat.parameters) == 3

    # Now stratify again, but this time with a subset of the concepts
    tm_strat2 = stratify(tm_strat,
                         key='superspreader',
                         strata=['superspreader', 'not_superspreader'],
                         structure=[],
                         cartesian_control=True,
                         directed=True,
                         # Only stratify beta for superspreaders vs
                         # non-superspreaders
                         params_to_stratify={p for p in tm_strat.parameters
                                             if p == 'beta'},
                         # For the sake of the test, lets say only old
                         # people can be superspreaders
                         concepts_to_stratify={
                             c.name for c in
                             tm_strat.get_concepts_name_map().values()
                             if c.name.startswith('infected') and
                                c.name.endswith('old')}
                         )

    # Delete illegal transitions:
    # - I_young -> I_old_superspreader
    # - I_young -> I_old_not_superspreader
    # - I_old_superspreader -> I_young
    # - I_old_not_superspreader -> I_young
    # - I_old_superspreader -> I_old_not_superspreader
    # - I_old_not_superspreader -> I_old_superspreader
    def _illegal_transitions(t: Template) -> bool:
        if isinstance(t, (ControlledConversion, NaturalConversion)):
            for inf1, inf2 in itertools.permutations(
                    ['infected_young', 'infected_old_superspreader',
                        'infected_old_not_superspreader'], 2):
                if t.subject.name == inf1 and t.outcome.name == inf2:
                    return True
        return False

    templates_to_delete = {
        t.get_key(): t for t in tm_strat2.templates if _illegal_transitions(t)
    }

    tm_strat2.templates = [
        t for t in tm_strat2.templates if t.get_key() not in templates_to_delete
    ]

    # We should have 7 concepts:
    # S_young, S_old, I_young, I_old_superspreader, I_old_not_superspreader,
    # R_young, R_old
    GraphicalModel.from_template_model(tm_strat2).write(
        './partial_strat_test.png')
    assert len(tm_strat2.get_concepts_map()) == 7

    # check that the original beta is present
    assert 'beta' in tm_strat2.parameters

    # check that all parameters are present in the rate laws
    for param in tm_strat2.parameters:
        found = False
        for t in tm_strat2.templates:
            for symb in t.rate_law.atoms():
                symb_str = str(symb)
                if symb_str == param:
                    found = True
                    break
            if found:
                break
        assert found, 'Parameter %s not found in any rate law' % param

    # Now check that all transitions have a corresponding parameter
    param_set = set(tm_strat2.parameters)
    for t in tm_strat2.templates:
        found = False
        for symb in t.rate_law.atoms():
            symb_str = str(symb)
            if symb_str in param_set:
                found = True
                break
        assert found, 'Transition %s has no corresponding parameter' % t
