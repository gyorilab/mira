"""Tests for operations on template models."""

import unittest
from collections import Counter
from copy import deepcopy as _d

import sympy

from mira.metamodel import (
    Concept,
    ControlledConversion,
    GroupedControlledConversion,
    Initial,
    Parameter,
    GroupedControlledProduction,
)
from mira.metamodel.template_model import TemplateModel
from mira.examples.sir import cities, sir, sir_2_city, sir_parameterized
from mira.examples.concepts import infected, susceptible
from mira.examples.chime import sviivr
from mira.metamodel.ops import stratify, simplify_rate_law


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
            rate_law=sympy.parse_expr(
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
            rate_law=sympy.parse_expr(
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
            rate_law=sympy.parse_expr(
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
            rate_law=sympy.parse_expr(
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
            rate_law=sympy.parse_expr(
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
                                                     do_rename=True), value=5.0,
                ),
                f"{susceptible.name}_unvaccinated": Initial(
                    concept=susceptible.with_context(vaccination_status="unvaccinated",
                                                     do_rename=True), value=5.0,
                ),
                f"{infected.name}_vaccinated": Initial(
                    concept=infected.with_context(vaccination_status="vaccinated",
                                                  do_rename=True), value=7.0,
                ),
                f"{infected.name}_unvaccinated": Initial(
                    concept=infected.with_context(vaccination_status="unvaccinated",
                                                  do_rename=True), value=7.0,
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
                f"{susceptible.name}_vaccinated": 5.0,
                f"{susceptible.name}_unvaccinated": 5.0,
                f"{infected.name}_vaccinated": 7.0,
                f"{infected.name}_unvaccinated": 7.0,
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
            key = f"{original_name}_{city}"
            self.assertIn(key, actual.initials, msg="")
            self.assertEqual(
                sir_parameterized.initials[original_name].value,
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
            rate_law=sympy.parse_expr('1.0*Susceptible*(Ailing*gamma + '
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
