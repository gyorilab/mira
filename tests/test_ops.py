"""Tests for operations on template models."""

import unittest

import sympy

from metamodel import NaturalConversion, TemplateModel
from mira.metamodel import (
    Concept,
    ControlledConversion,
    GroupedControlledConversion,
    Parameter,
    GroupedControlledProduction,
)
from mira.examples.sir import cities, sir, sir_2_city, infected, infection, recovery
from mira.examples.chime import sviivr
from mira.metamodel.ops import stratify, simplify_rate_law


def _s(s):
    return sympy.Symbol(s)


class TestOperations(unittest.TestCase):
    """A test case for operations on template models."""

    def test_stratify(self):
        """Test stratifying a template model by labels."""
        actual = stratify(sir, key="city", strata=cities, cartesian_control=False, directed=False)
        self.assertEqual(
            {template.get_key() for template in sir_2_city.templates},
            {template.get_key() for template in actual.templates},
        )

    def test_stratify_control(self):
        """Test stratifying a template that properly multiples the controllers."""
        actual = stratify(
            sir,
            key="vaccination_status",
            strata={"vaccinated", "unvaccinated"},
            structure=[],  # i.e., don't add any conversions
            cartesian_control=True,  # i.e., cross-product control based on strata
        )
        self.assertEqual(
            {template.get_key() for template in sviivr.templates},
            {template.get_key() for template in actual.templates},
        )

        # Check that no group conversions have duplicate controllers
        for template in actual.templates:
            if not isinstance(
                template,
                (GroupedControlledConversion, GroupedControlledProduction)
            ):
                continue
            raise NotImplementedError

    def test_stratify_with_exclude(self):
        """Test stratifying a template that properly multiples the controllers."""
        dead = Concept(name="dead", identifiers={"ncit": "C28554"})
        sird = sir.add_transition(infected, dead)
        actual = stratify(
            sird,
            key="vaccination_status",
            strata={"vaccinated", "unvaccinated"},
            structure=[],  # i.e., don't add any conversions
            exclude=[dead],
            cartesian_control=True,
        )
        expected = TemplateModel(
            templates=[
                infection.with_context(vaccination_status="vaccinated"),
                infection.with_context(vaccination_status="unvaccinated"),
                infection.with_context(vaccination_status="vaccinated"),
                infection.with_context(vaccination_status="unvaccinated"),
                NaturalConversion(subject=infected.with_context(vaccination_status="vaccinated"), outcome=dead),
                NaturalConversion(subject=infected.with_context(vaccination_status="unvaccinated"), outcome=dead),
            ]
        )
        self.assertEqual(
            {template.get_key() for template in expected.templates},
            {template.get_key() for template in actual.templates},
        )

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
