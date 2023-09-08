import unittest
import requests
import pytest
from copy import deepcopy as _d
from mira.modeling.askenet.ops import *
from sympy import *
from mira.metamodel.io import mathml_to_expression
from mira.metamodel.templates import Concept


class TestAskenetOperations(unittest.TestCase):
    """A test case for operations on template models."""

    @classmethod
    def setUpClass(cls):
        cls.sir_amr = requests.get(
            'https://raw.githubusercontent.com/DARPA-ASKEM/'
            'Model-Representations/main/petrinet/examples/sir.json').json()

    '''These unit tests are conducted by zipping through lists of each key in a amr file
        (e.g. parameters, observables, etc). Zipping in this manner assumes that the order (assuming insertion order)
        is preserved before and after mira operation for an amr key
    '''

    def test_replace_state_id(self):
        old_id = 'S'
        new_id = 'X'
        amr = _d(self.sir_amr)
        new_amr = replace_state_id(amr, old_id, new_id)

        old_model = amr['model']
        new_model = new_amr['model']

        old_model_states = old_model['states']
        new_model_states = new_model['states']

        old_model_transitions = old_model['transitions']
        new_model_transitions = new_model['transitions']

        self.assertEqual(len(old_model_states), len(new_model_states))
        for old_state, new_state in zip(old_model_states, new_model_states):

            # output states missing description field
            if old_state['id'] == old_id:
                self.assertEqual(new_state['id'], new_id)
                self.assertEqual(old_state['name'], new_state['name'])
                self.assertEqual(old_state['grounding']['identifiers'], new_state['grounding']['identifiers'])
                self.assertEqual(old_state['units'], new_state['units'])

        self.assertEqual(len(old_model_transitions), len(new_model_transitions))

        # output transitions are missing a description and transition['properties']['name'] field
        # is abbreviated in output amr
        for old_transition, new_transition in zip(old_model_transitions, new_model_transitions):
            if old_id in old_transition['input'] or old_id in old_transition['output']:
                self.assertIn(new_id, new_transition['input'])
                self.assertNotIn(old_id, new_transition['output'])
                self.assertEqual(len(old_transition['input']), len(new_transition['input']))
                self.assertEqual(len(old_transition['output']), len(new_transition['output']))
                self.assertEqual(old_transition['id'], new_transition['id'])

        old_semantics_ode = amr['semantics']['ode']
        new_semantics_ode = new_amr['semantics']['ode']

        old_semantics_ode_rates = old_semantics_ode['rates']
        new_semantics_ode_rates = new_semantics_ode['rates']

        # this test doesn't account for if the expression semantic is preserved (e.g. same type of operations)
        # would pass test if we call replace_state_id(I,J) and old expression is "I*X" and new expression is "J+X"
        for old_rate, new_rate in zip(old_semantics_ode_rates, new_semantics_ode_rates):
            if old_id in old_rate['expression'] or old_id in old_rate['expression_mathml']:
                self.assertIn(new_id, new_rate['expression'])
                self.assertNotIn(old_id, new_rate['expression'])

                self.assertIn(new_id, new_rate['expression_mathml'])
                self.assertNotIn(old_id, new_rate['expression_mathml'])

                self.assertEqual(old_rate['target'], new_rate['target'])

        # initials have float values substituted in for state ids in their expression and expression_mathml field
        old_semantics_ode_initials = old_semantics_ode['initials']
        new_semantics_ode_initials = new_semantics_ode['initials']

        self.assertEqual(len(old_semantics_ode_initials), len(new_semantics_ode_initials))
        for old_initials, new_initials in zip(old_semantics_ode_initials, new_semantics_ode_initials):
            if old_id == old_initials['target']:
                self.assertEqual(new_initials['target'], new_id)

        old_semantics_ode_parameters = old_semantics_ode['parameters']
        new_semantics_ode_parameters = new_semantics_ode['parameters']
        # This is due to initial expressions vs values
        assert len(old_semantics_ode_parameters) == 5
        assert len(new_semantics_ode_parameters) == 2

        # zip method iterates over length of the smaller iterable len(new_semantics_ode_parameters) = 2
        # as opposed to len(old_semantics_ode_parameters) = 5 , non-state parameters are listed first in input amr
        for old_params, new_params in zip(old_semantics_ode_parameters, new_semantics_ode_parameters):
            # test to see if old_id/new_id in name/id field and not for id/name equality because these fields
            # may contain subscripts or timestamps appended to the old_id/new_id
            if old_id in old_params['id'] and old_id in old_params['name']:
                self.assertIn(new_id, new_params['id'])
                self.assertIn(new_id, new_params['name'])

        old_semantics_ode_observables = old_semantics_ode['observables']
        new_semantics_ode_observables = new_semantics_ode['observables']
        self.assertEqual(len(old_semantics_ode_observables), len(new_semantics_ode_observables))

        for old_observable, new_observable in zip(old_semantics_ode_observables, new_semantics_ode_observables):
            if old_id in old_observable['states'] and old_id in old_observable['expression'] and \
                    old_id in old_observable['expression_mathml']:
                self.assertIn(new_id, new_observable['expression'])
                self.assertNotIn(old_id, new_observable['expression'])

                self.assertIn(new_id, new_observable['expression_mathml'])
                self.assertNotIn(old_id, new_observable['expression_mathml'])

                self.assertEqual(old_observable['id'], new_observable['id'])

    def test_replace_transition_id(self):

        old_id = 'inf'
        new_id = 'new_inf'
        amr = _d(self.sir_amr)
        new_amr = replace_transition_id(amr, old_id, new_id)

        old_model_transitions = amr['model']['transitions']
        new_model_transitions = new_amr['model']['transitions']

        self.assertEqual(len(old_model_transitions), len(new_model_transitions))

        for old_transitions, new_transition in zip(old_model_transitions, new_model_transitions):
            if old_transitions['id'] == old_id:
                self.assertEqual(new_transition['id'], new_id)

    def test_replace_observable_id(self):
        old_id = 'noninf'
        new_id = 'testinf'
        new_display_name = 'test-infection'
        amr = _d(self.sir_amr)
        new_amr = replace_observable_id(amr, old_id, new_id,
                                        name=new_display_name)

        old_semantics_observables = amr['semantics']['ode']['observables']
        new_semantics_observables = new_amr['semantics']['ode']['observables']

        self.assertEqual(len(old_semantics_observables), len(new_semantics_observables))

        for old_observable, new_observable in zip(old_semantics_observables, new_semantics_observables):
            if old_observable['id'] == old_id:
                self.assertEqual(new_observable['id'], new_id)
                self.assertEqual(new_observable['name'], new_display_name)

    def test_remove_observable_or_parameter(self):

        old_amr_obs = _d(self.sir_amr)
        old_amr_param = _d(self.sir_amr)

        replaced_observable_id = 'noninf'
        new_amr_obs = remove_observable(old_amr_obs, replaced_observable_id)
        for new_observable in new_amr_obs['semantics']['ode']['observables']:
            self.assertNotEqual(new_observable['id'], replaced_observable_id)

        replaced_param_id = 'beta'
        replacement_value = 5
        new_amr_param = remove_parameter(old_amr_param, replaced_param_id, replacement_value)
        for new_param in new_amr_param['semantics']['ode']['parameters']:
            self.assertNotEqual(new_param['id'], replaced_param_id)
        for old_rate, new_rate in zip(old_amr_param['semantics']['ode']['rates'],
                                      new_amr_param['semantics']['ode']['rates']):
            if replaced_param_id in old_rate['expression'] and replaced_param_id in old_rate['expression_mathml']:
                self.assertNotIn(replaced_param_id, new_rate['expression'])
                self.assertIn(str(replacement_value), new_rate['expression'])

                self.assertNotIn(replaced_param_id, new_rate['expression_mathml'])
                self.assertIn(str(replacement_value), new_rate['expression_mathml'])

                self.assertEqual(old_rate['target'], new_rate['target'])

        # currently don't support expressions for initials
        for old_obs, new_obs in zip(old_amr_param['semantics']['ode']['observables'],
                                    new_amr_param['semantics']['ode']['observables']):
            if replaced_param_id in old_obs['expression'] and replaced_param_id in old_obs['expression_mathml']:
                self.assertNotIn(replaced_param_id, new_obs['expression'])
                self.assertIn(str(replacement_value), new_obs['expression'])

                self.assertNotIn(replaced_param_id, new_obs['expression_mathml'])
                self.assertIn(str(replacement_value), new_obs['expression_mathml'])

                self.assertEqual(old_obs['id'], new_obs['id'])

    @pytest.mark.sbmlmath
    def test_add_observable(self):
        amr = _d(self.sir_amr)
        new_id = 'testinf'
        new_display_name = 'DISPLAY_TEST'
        xml_expression = "<apply><times/><ci>E</ci><ci>delta</ci></apply>"
        new_amr = add_observable(amr, new_id, new_display_name, xml_expression)

        # Create a dict out of a list of observable dict entries to easier test for addition of new observables
        new_observable_dict = {}
        for observable in new_amr['semantics']['ode']['observables']:
            name = observable.pop('id')
            new_observable_dict[name] = observable

        self.assertIn(new_id, new_observable_dict)
        self.assertEqual(new_display_name, new_observable_dict[new_id]['name'])
        self.assertEqual(xml_expression, new_observable_dict[new_id]['expression_mathml'])
        self.assertEqual(sstr(mathml_to_expression(xml_expression)), new_observable_dict[new_id]['expression'])

    @pytest.mark.sbmlmath
    def test_replace_parameter_id(self):
        old_id = 'beta'
        new_id = 'TEST'
        amr = _d(self.sir_amr)
        new_amr = replace_parameter_id(amr, old_id, new_id)

        old_semantics_ode_rates = amr['semantics']['ode']['rates']
        new_semantics_ode_rates = new_amr['semantics']['ode']['rates']

        old_semantics_ode_observables = amr['semantics']['ode']['observables']
        new_semantics_ode_observables = new_amr['semantics']['ode']['observables']

        old_semantics_ode_parameters = amr['semantics']['ode']['parameters']
        new_semantics_ode_parameters = new_amr['semantics']['ode']['parameters']

        new_model_states = new_amr['model']['states']

        self.assertEqual(len(old_semantics_ode_rates), len(new_semantics_ode_rates))
        self.assertEqual(len(old_semantics_ode_observables), len(new_semantics_ode_observables))

        self.assertEqual(len(old_semantics_ode_parameters) - len(new_model_states), len(new_semantics_ode_parameters))

        for old_rate, new_rate in zip(old_semantics_ode_rates, new_semantics_ode_rates):
            if old_id in old_rate['expression'] and old_id in old_rate['expression_mathml']:
                self.assertIn(new_id, new_rate['expression'])
                self.assertNotIn(old_id, new_rate['expression'])

                self.assertIn(new_id, new_rate['expression_mathml'])
                self.assertNotIn(old_id, new_rate['expression_mathml'])

        # don't test states field for a parameter as it is assumed that replace_parameter_id will only be used with
        # parameters such as gamma or beta (i.e. non-states)
        for old_observable, new_observable in zip(old_semantics_ode_observables, new_semantics_ode_observables):
            if old_id in old_observable['expression'] and old_id in new_observable['expression_mathml']:
                self.assertIn(new_id, new_observable['expression'])
                self.assertNotIn(old_id, new_observable['expression'])

                self.assertIn(new_id, new_observable['expression_mathml'])
                self.assertNotIn(old_id, new_observable['expression_mathml'])

        for old_parameter, new_parameter in zip(old_semantics_ode_parameters, new_semantics_ode_parameters):
            if old_parameter['id'] == old_id:
                self.assertEqual(new_parameter['id'], new_id)
                self.assertEqual(old_parameter['value'], new_parameter['value'])
                self.assertEqual(old_parameter['distribution'], new_parameter['distribution'])
                self.assertEqual(sstr(old_parameter['units']['expression']), new_parameter['units']['expression'])
                self.assertEqual(mathml_to_expression(old_parameter['units']['expression_mathml']),
                                 mathml_to_expression(new_parameter['units']['expression_mathml']))

    @pytest.mark.sbmlmath
    def test_add_parameter(self):
        amr = _d(self.sir_amr)

        new_amr = add_parameter(amr, parameter_id='sigma',
                                expression_xml="<apply><times/><ci>E</ci><ci>delta</ci></apply>",
                                value=.5, distribution_type='Uniform1', min_value=.05, max_value=.8)

    def test_remove_state(self):
        removed_state_id = 'S'
        amr = _d(self.sir_amr)

        new_amr = remove_state(amr, removed_state_id)

        new_model = new_amr['model']
        new_model_states = new_model['states']
        new_model_transitions = new_model['transitions']

        new_semantics_ode = new_amr['semantics']['ode']
        new_semantics_ode_rates = new_semantics_ode['rates']
        new_semantics_ode_initials = new_semantics_ode['initials']
        new_semantics_ode_parameters = new_semantics_ode['parameters']
        new_semantics_ode_observables = new_semantics_ode['observables']

        for new_state in new_model_states:
            self.assertNotEquals(removed_state_id, new_state['id'])

        for new_transition in new_model_transitions:
            self.assertNotIn(removed_state_id, new_transition['input'])
            self.assertNotIn(removed_state_id, new_transition['output'])

        # output rates that originally contained targeted state are removed
        for new_rate in new_semantics_ode_rates:
            self.assertNotIn(removed_state_id, new_rate['expression'])
            self.assertNotIn(removed_state_id, new_rate['expression_mathml'])

        # initials are bugged, all states removed rather than just targeted removed state in output amr
        for new_initial in new_semantics_ode_initials:
            self.assertNotEquals(removed_state_id, new_initial['target'])

        # parameters that are associated in an expression with a removed state are not present in output amr
        # (e.g.) if there exists an expression: "S*I*beta" and we remove S, then beta is no longer present in output
        # list of parameters
        for new_parameter in new_semantics_ode_parameters:
            self.assertNotIn(removed_state_id, new_parameter['id'])

        # output observable expressions that originally contained targeted state still exist with targeted state removed
        # (e.g. 'S+R' -> 'R') if 'S' is the removed state
        for new_observable in new_semantics_ode_observables:
            self.assertNotIn(removed_state_id, new_observable['expression'])
            self.assertNotIn(removed_state_id, new_observable['expression_mathml'])

    def test_remove_transition(self):
        removed_transition = 'inf'
        amr = _d(self.sir_amr)

        new_amr = remove_transition(amr, removed_transition)
        new_model_transition = new_amr['model']['transitions']

        for new_transition in new_model_transition:
            self.assertNotEquals(removed_transition, new_transition['id'])

    @pytest.mark.sbmlmath
    def test_add_transition(self):
        test_subject = Concept(name="test_subject", identifiers={"ido": "0000511"})
        test_outcome = Concept(name="test_outcome", identifiers={"ido": "0000592"})
        expression_xml = "<apply><times/><ci>E</ci><ci>delta</ci></apply>"
        new_transition_id = 'test'
        old_natural_conversion_amr = _d(self.sir_amr)
        old_natural_production_amr = _d(self.sir_amr)
        old_natural_degradation_amr = _d(self.sir_amr)

        # NaturalConversion
        new_natural_conversion_amr = add_transition(old_natural_conversion_amr, new_transition_id, expression_xml,
                                                    src_id=test_subject,
                                                    tgt_id=test_outcome)
        natural_conversion_transition_dict = {}
        natural_conversion_rates_dict = {}
        natural_conversion_state_dict = {}

        for transition in new_natural_conversion_amr['model']['transitions']:
            name = transition.pop('id')
            natural_conversion_transition_dict[name] = transition

        for rate in new_natural_conversion_amr['semantics']['ode']['rates']:
            name = rate.pop('target')
            natural_conversion_rates_dict[name] = rate

        for state in new_natural_conversion_amr['model']['states']:
            name = state.pop('id')
            natural_conversion_state_dict[name] = state

        self.assertIn(new_transition_id, natural_conversion_transition_dict)
        self.assertIn(new_transition_id, natural_conversion_rates_dict)
        self.assertEqual(expression_xml, natural_conversion_rates_dict[new_transition_id]['expression_mathml'])
        self.assertEqual(sstr(mathml_to_expression(expression_xml)),
                         natural_conversion_rates_dict[new_transition_id]['expression'])
        self.assertIn(test_subject.name, natural_conversion_state_dict)
        self.assertIn(test_outcome.name, natural_conversion_state_dict)

        # NaturalProduction
        new_natural_production_amr = add_transition(old_natural_production_amr, new_transition_id, expression_xml,
                                                    tgt_id=test_outcome)
        natural_production_transition_dict = {}
        natural_production_rates_dict = {}
        natural_production_state_dict = {}

        for transition in new_natural_production_amr['model']['transitions']:
            name = transition.pop('id')
            natural_production_transition_dict[name] = transition

        for rate in new_natural_production_amr['semantics']['ode']['rates']:
            name = rate.pop('target')
            natural_production_rates_dict[name] = rate

        for state in new_natural_production_amr['model']['states']:
            name = state.pop('id')
            natural_production_state_dict[name] = state

        self.assertIn(new_transition_id, natural_production_transition_dict)
        self.assertIn(new_transition_id, natural_production_rates_dict)
        self.assertEqual(expression_xml, natural_production_rates_dict[new_transition_id]['expression_mathml'])
        self.assertEqual(sstr(mathml_to_expression(expression_xml)),
                         natural_production_rates_dict[new_transition_id]['expression'])
        self.assertIn(test_outcome.name, natural_production_state_dict)

        # NaturalDegradation
        new_natural_degradation_amr = add_transition(old_natural_degradation_amr, new_transition_id, expression_xml,
                                                     src_id=test_subject)
        natural_degradation_transition_dict = {}
        natural_degradation_rates_dict = {}
        natural_degradation_states_dict = {}

        for transition in new_natural_degradation_amr['model']['transitions']:
            name = transition.pop('id')
            natural_degradation_transition_dict[name] = transition

        for rate in new_natural_degradation_amr['semantics']['ode']['rates']:
            name = rate.pop('target')
            natural_degradation_rates_dict[name] = rate

        for state in new_natural_degradation_amr['model']['states']:
            name = state.pop('id')
            natural_degradation_states_dict[name] = state

        self.assertIn(new_transition_id, natural_degradation_transition_dict)
        self.assertIn(new_transition_id, natural_degradation_rates_dict)
        self.assertEqual(expression_xml, natural_degradation_rates_dict[new_transition_id]['expression_mathml'])
        self.assertEqual(sstr(mathml_to_expression(expression_xml)),
                         natural_degradation_rates_dict[new_transition_id]['expression'])
        self.assertIn(test_subject.name, natural_degradation_states_dict)

    @pytest.mark.sbmlmath
    def test_replace_rate_law_sympy(self):
        transition_id = 'inf'
        target_expression_xml_str = '<apply><plus/><ci>X</ci><cn>8</cn></apply>'
        target_expression_sympy = mathml_to_expression(target_expression_xml_str)

        amr = _d(self.sir_amr)
        new_amr = replace_rate_law_sympy(amr, transition_id, target_expression_sympy)
        new_semantics_ode_rates = new_amr['semantics']['ode']['rates']

        for new_rate in new_semantics_ode_rates:
            if new_rate['target'] == transition_id:
                self.assertEqual(sstr(target_expression_sympy), new_rate['expression'])
                self.assertEqual(target_expression_xml_str, new_rate['expression_mathml'])

    @pytest.mark.sbmlmath
    def test_replace_rate_law_mathml(self):
        amr = _d(self.sir_amr)
        transition_id = 'inf'
        target_expression_xml_str = "<apply><times/><ci>E</ci><ci>delta</ci></apply>"
        target_expression_sympy = mathml_to_expression(target_expression_xml_str)

        new_amr = replace_rate_law_mathml(amr, transition_id, target_expression_xml_str)

        new_semantics_ode_rates = new_amr['semantics']['ode']['rates']

        for new_rate in new_semantics_ode_rates:
            if new_rate['target'] == transition_id:
                self.assertEqual(sstr(target_expression_sympy), new_rate['expression'])
                self.assertEqual(target_expression_xml_str, new_rate['expression_mathml'])

    @pytest.mark.sbmlmath
    # Following 2 unit tests only test for replacing expressions in observables, not initials
    def test_replace_expression_sympy(self):
        object_id = 'noninf'
        amr = _d(self.sir_amr)
        target_expression_xml_str = "<apply><times/><ci>E</ci><ci>beta</ci></apply>"
        target_expression_sympy = mathml_to_expression(target_expression_xml_str)
        new_amr = replace_expression_sympy(amr, object_id, target_expression_sympy, False)

        for new_obs in new_amr['semantics']['ode']['observables']:
            if new_obs['id'] == object_id:
                self.assertEqual(sstr(target_expression_sympy), new_obs['expression'])
                self.assertEqual(target_expression_xml_str, new_obs['expression_mathml'])

    @pytest.mark.sbmlmath
    def test_replace_expression_mathml(self):
        object_id = 'noninf'
        amr = _d(self.sir_amr)
        target_expression_xml_str = "<apply><times/><ci>E</ci><ci>beta</ci></apply>"
        target_expression_sympy = mathml_to_expression(target_expression_xml_str)
        new_amr = replace_expression_mathml(amr, object_id, target_expression_xml_str, False)

        for new_obs in new_amr['semantics']['ode']['observables']:
            if new_obs['id'] == object_id:
                self.assertEqual(sstr(target_expression_sympy), new_obs['expression'])
                self.assertEqual(target_expression_xml_str, new_obs['expression_mathml'])

    def test_stratify(self):
        amr = _d(self.sir_amr)
        new_amr = stratify(amr, key='city', strata=['boston', 'nyc'])

        self.assertIsInstance(amr, dict)
        self.assertIsInstance(new_amr, dict)

    def test_simplify_rate_laws(self):
        amr = _d(self.sir_amr)
        new_amr = simplify_rate_laws(amr)

        self.assertIsInstance(amr, dict)
        self.assertIsInstance(new_amr, dict)

    def test_aggregate_parameters(self):
        amr = _d(self.sir_amr)
        new_amr = aggregate_parameters(amr)

        self.assertIsInstance(amr, dict)
        self.assertIsInstance(new_amr, dict)

    def test_counts_to_dimensionless(self):
        amr = _d(self.sir_amr)
        new_amr = counts_to_dimensionless(amr, 'ml', .8)
        self.assertIsInstance(amr, dict)
        self.assertIsInstance(new_amr, dict)
