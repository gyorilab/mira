import unittest
import requests
from copy import deepcopy as _d
from mira.modeling.askenet.ops import *


class TestAskenetOperations(unittest.TestCase):
    """A test case for operations on template models."""

    @classmethod
    def setUpClass(cls):
        cls.sir_amr = requests.get(
            'https://raw.githubusercontent.com/DARPA-ASKEM/'
            'Model-Representations/main/petrinet/examples/sir.json').json()

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
            if old_state['id'] == old_id:
                self.assertEqual(new_state['id'], new_id)

        self.assertEqual(len(old_model_transitions), len(new_model_transitions))
        for old_transition, new_transition in zip(old_model_transitions, new_model_transitions):
            if old_id in old_transition['input']:
                new_value_in_transition_input = new_id in new_transition['input']
                old_value_out_transition_input = old_id not in new_transition['input']
                equal_length_input = (len(old_transition['input']) == len(new_transition['input']))

                self.assertTrue(new_value_in_transition_input and old_value_out_transition_input and equal_length_input)
            if old_id in old_transition['output']:
                new_value_in_transition_output = new_id in new_transition['output']
                old_value_out_transition_output = old_id not in new_transition['output']
                equal_length_output = (len(old_transition['output']) == len(new_transition['output']))

                self.assertTrue(
                    new_value_in_transition_output and old_value_out_transition_output and equal_length_output)

        old_semantics_ode = amr['semantics']['ode']
        new_semantics_ode = new_amr['semantics']['ode']

        old_semantics_ode_rates = old_semantics_ode['rates']
        new_semantics_ode_rates = new_semantics_ode['rates']

        # this test doesn't account for if the expression semantic is preserved (e.g. same type of operations)
        # would pass test if we call replace_state_id(I,J) and old expression is "I*X" and new expression is "J+X"
        for old_rate, new_rate in zip(old_semantics_ode_rates, new_semantics_ode_rates):
            if (old_id in old_rate['expression']) or (old_id in old_rate['expression_mathml']):
                new_value_in_rate_expression = (new_id in new_rate['expression'])
                old_value_out_rate_expression = (old_id not in new_rate['expression'])
                expression_flag = (new_value_in_rate_expression and old_value_out_rate_expression)

                new_value_in_rate_mathml = (new_id in new_rate['expression_mathml'])
                old_value_out_rate_mathml = (old_id not in new_rate['expression_mathml'])
                mathml_flag = (new_value_in_rate_mathml and old_value_out_rate_mathml)

                self.assertTrue(expression_flag and mathml_flag)

        # for initials, the dict representing states in the initials list have changed expression values in new_amr
        # from variables to float values
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
        # state id and name for each parameter dict in list of parameters has a '0' appended to it (not 'S' but 'S0')
        # so test for equality with 0 and subscript ₀ appended to old state id (assuming that 0 and subscript are
        # timestamps that will be constantly changing) and then taste if new state id and name field for each
        # parameter is equal to just state id

        # Currently this test passes no matter what as zip function only iterates over the shorter of two lists
        # since output only has 2 entries (parameter entries of beta and gamma) as opposed to 5 from
        # old amr, this test will pass
        for old_params, new_params in zip(old_semantics_ode_parameters, new_semantics_ode_parameters):
            if ((old_id + '0') in old_params['id']) or ((old_id + '₀') in old_params['name']):
                self.assertEqual(new_id, new_params['id'])
                self.assertEqual(new_id, new_params['name'])

        old_semantics_ode_observables = old_semantics_ode['observables']
        new_semantics_ode_observables = new_semantics_ode['observables']
        self.assertEqual(len(old_semantics_ode_observables), len(new_semantics_ode_observables))

        # each observable dict in list of observables in new amr does not have the states key which is a list of states
        # expression for each observable has an extra space between states in new_amr
        for old_observable, new_observable in zip(old_semantics_ode_observables, new_semantics_ode_observables):
            if (old_id in old_observable['states']) or (old_id in old_observable['expression']) or \
                    (old_id in old_observable['expression_mathml']):
                new_value_in_observable_expression = (new_id in new_observable['expression'])
                old_value_out_observable_expression = (old_id not in new_observable['expression'])
                expression_flag = (new_value_in_observable_expression and old_value_out_observable_expression)

                new_value_in_observable_mathml = new_id in new_observable['expression_mathml']
                old_value_out_observable_mathml = old_id not in new_observable['expression_mathml']
                mathml_flag = (new_value_in_observable_mathml and old_value_out_observable_mathml)

                self.assertTrue(expression_flag and mathml_flag)

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

    # checks for updated id and name field of an observable - suggested change in method definition
    # such that we can use a different value for name rather than reusing new_id
    def test_replace_observable_id(self):
        old_id = 'noninf'
        new_id = 'testinf'
        amr = _d(self.sir_amr)
        new_amr = replace_observable_id(amr, old_id, new_id)

        old_semantics_observables = amr['semantics']['ode']['observables']
        new_semantics_observables = new_amr['semantics']['ode']['observables']

        self.assertEqual(len(old_semantics_observables), len(new_semantics_observables))

        for old_observable, new_observable in zip(old_semantics_observables, new_semantics_observables):
            if old_observable['id'] == old_id:
                self.assertEqual(new_observable['id'], new_id) and self.assertEqual(new_observable['name'], new_id)

    def test_replace_parameter_id(self):
        old_id = 'beta'
        new_id = 'zeta'
        amr = _d(self.sir_amr)
        new_amr = replace_parameter_id(amr, old_id, new_id)

        old_semantics_ode_rates = amr['semantics']['ode']['rates']
        new_semantics_ode_rates = new_amr['semantics']['ode']['rates']

        old_semantics_ode_observables = amr['semantics']['ode']['observables']
        new_semantics_ode_observables = new_amr['semantics']['ode']['observables']

        self.assertEqual(len(old_semantics_ode_rates), len(new_semantics_ode_rates))

        for old_rate, new_rate in zip(old_semantics_ode_rates, new_semantics_ode_rates):
            if old_id in old_rate['expression'] and old_id in old_rate['expression_mathml']:
                new_value_in_rate_expression = new_id in new_rate['expression']
                old_value_out_rate_expression = old_id not in new_rate['expression']

                expression_flag = (new_value_in_rate_expression and old_value_out_rate_expression)

                new_value_in_rate_mathml = new_id in new_rate['expression_mathml']
                old_value_out_rate_mathml = old_id not in new_rate['expression_mathml']

                mathml_flag = (new_value_in_rate_mathml and old_value_out_rate_mathml)

                self.assertTrue(expression_flag and mathml_flag)

        for old_observable, new_observable in zip(old_semantics_ode_observables, new_semantics_ode_observables):

            if (old_id in old_observable['states'] and
                    old_id in old_observable['expression'] and old_id in new_observable['expression_mathml']):
                new_value_in_observable_expression = new_id in new_observable['expression']
                old_value_out_observable_expression = old_id not in new_observable['expression']

                expression_flag = (new_value_in_observable_expression and old_value_out_observable_expression)

                new_value_in_observable_mathml = new_id in new_observable['expression_mathml']
                old_value_out_observable_mathml = old_id not in new_observable['expression_mathml']

                mathml_flag = (new_value_in_observable_mathml and old_value_out_observable_mathml)

                self.assertTrue(expression_flag and mathml_flag)
