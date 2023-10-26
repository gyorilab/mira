import unittest
import requests
from copy import deepcopy as _d
from mira.modeling.amr.ops import *
from mira.metamodel.io import mathml_to_expression
from mira.metamodel.decapodes import Variable, Op1, Op2

try:
    import sbmlmath
except ImportError:
    sbmlmath_available = False
else:
    sbmlmath_available = True

SBMLMATH_REQUIRED = unittest.skipUnless(sbmlmath_available, reason="SBMLMath package is not available")


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

        old_semantics_ode_initials = old_semantics_ode['initials']
        new_semantics_ode_initials = new_semantics_ode['initials']

        self.assertEqual(len(old_semantics_ode_initials), len(new_semantics_ode_initials))
        for old_initials, new_initials in zip(old_semantics_ode_initials, new_semantics_ode_initials):
            if old_id == old_initials['target']:
                self.assertEqual(new_initials['target'], new_id)
                self.assertEqual(old_initials['expression'], new_initials['expression'])
                self.assertEqual(old_initials['expression_mathml'], new_initials['expression_mathml'])

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

    def test_remove_observable(self):
        amr = _d(self.sir_amr)
        replaced_observable_id = 'noninf'
        new_amr = remove_observable(amr, replaced_observable_id)
        for new_observable in new_amr['semantics']['ode']['observables']:
            self.assertNotEqual(new_observable['id'], replaced_observable_id)

    def test_remove_parameter(self):

        amr = _d(self.sir_amr)

        removed_param_id = 'beta'
        replacement_value = 5
        new_amr = remove_parameter(amr, removed_param_id, replacement_value)
        for new_param in new_amr['semantics']['ode']['parameters']:
            self.assertNotEqual(new_param['id'], removed_param_id)

        for old_rate, new_rate in zip(amr['semantics']['ode']['rates'],
                                      new_amr['semantics']['ode']['rates']):
            if removed_param_id in old_rate['expression'] and removed_param_id in old_rate['expression_mathml']:
                self.assertNotIn(removed_param_id, new_rate['expression'])
                self.assertIn(str(replacement_value), new_rate['expression'])

                self.assertNotIn(removed_param_id, new_rate['expression_mathml'])
                self.assertIn(str(replacement_value), new_rate['expression_mathml'])

                self.assertEqual(old_rate['target'], new_rate['target'])

        for old_obs, new_obs in zip(amr['semantics']['ode']['observables'],
                                    new_amr['semantics']['ode']['observables']):
            if removed_param_id in old_obs['expression'] and removed_param_id in old_obs['expression_mathml']:
                self.assertNotIn(removed_param_id, new_obs['expression'])
                self.assertIn(str(replacement_value), new_obs['expression'])

                self.assertNotIn(removed_param_id, new_obs['expression_mathml'])
                self.assertIn(str(replacement_value), new_obs['expression_mathml'])

                self.assertEqual(old_obs['id'], new_obs['id'])

    def test_remove_parameter_initial(self):
        amr = _d(self.sir_amr)
        removed_param_id = 'S0'
        replacement_value = 100
        new_amr = remove_parameter(amr, removed_param_id, replacement_value)

        for new_param in new_amr['semantics']['ode']['parameters']:
            self.assertNotEqual(new_param['id'], removed_param_id)

        for old_initial, new_initial in zip(amr['semantics']['ode']['initials'],
                                            new_amr['semantics']['ode']['initials']):
            if removed_param_id in old_initial['expression'] and removed_param_id in old_initial['expression_mathml']:
                self.assertNotIn(removed_param_id, new_initial['expression'])
                self.assertIn(str(replacement_value), new_initial['expression'])

                self.assertNotIn(removed_param_id, new_initial['expression_mathml'])
                self.assertIn(str(replacement_value), new_initial['expression_mathml'])

    @SBMLMATH_REQUIRED
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
        self.assertEqual(str(mathml_to_expression(xml_expression)), new_observable_dict[new_id]['expression'])

    @SBMLMATH_REQUIRED
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

        self.assertEqual(len(old_semantics_ode_rates), len(new_semantics_ode_rates))
        self.assertEqual(len(old_semantics_ode_observables), len(new_semantics_ode_observables))

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

        old_param_dict = {}
        new_param_dict = {}

        for old_parameter, new_parameter in zip(old_semantics_ode_parameters, new_semantics_ode_parameters):
            old_name = old_parameter.pop('id')
            new_name = new_parameter.pop('id')

            old_param_dict[old_name] = old_parameter
            new_param_dict[new_name] = new_parameter

        self.assertIn(new_id, new_param_dict)
        self.assertNotIn(old_id, new_param_dict)

        self.assertEqual(old_param_dict[old_id]['value'], new_param_dict[new_id]['value'])
        self.assertEqual(old_param_dict[old_id]['distribution'], new_param_dict[new_id]['distribution'])
        self.assertEqual(str(old_param_dict[old_id]['units']['expression']),
                         new_param_dict[new_id]['units']['expression'])
        self.assertEqual(mathml_to_expression(old_param_dict[old_id]['units']['expression_mathml']),
                         mathml_to_expression(new_param_dict[new_id]['units']['expression_mathml']))

        old_initial_expression_id = 'S0'
        initial_expression_amr = _d(self.sir_amr)
        new_initial_expression_amr = replace_parameter_id(initial_expression_amr, old_initial_expression_id, new_id)
        old_initials = initial_expression_amr['semantics']['ode']['initials']
        new_initials = new_initial_expression_amr['semantics']['ode']['initials']
        for old_initial, new_initial in zip(old_initials, new_initials):
            if old_initial_expression_id in old_initial.get(
                'expression') and old_initial_expression_id in old_initial.get('expression_mathml'):
                self.assertNotIn(old_initial_expression_id, new_initial['expression'])
                self.assertNotIn(old_initial_expression_id, new_initial['expression_mathml'])

                self.assertIn(new_id, new_initial['expression'])
                self.assertIn(new_id, new_initial['expression_mathml'])

    @SBMLMATH_REQUIRED
    def test_add_parameter(self):
        amr = _d(self.sir_amr)
        parameter_id = 'TEST_ID'
        name = 'TEST_DISPLAY'
        description = 'TEST_DESCRIPTION'
        value = 0.35
        distribution = {'type': 'test_distribution',
                        'parameters': {'test_dist': 5}}
        new_amr = add_parameter(amr, parameter_id=parameter_id, name=name, description=description, value=value,
                                distribution=distribution)
        param_dict = {}
        for param in new_amr['semantics']['ode']['parameters']:
            popped_id = param.pop('id')
            param_dict[popped_id] = param

        # If param has a concept(i.e. is a rate parameter/in a rate law), we then associate units with the parameter
        self.assertIn(parameter_id, param_dict)
        self.assertEqual(param_dict[parameter_id]['name'], name)
        self.assertEqual(param_dict[parameter_id]['description'], description)
        self.assertEqual(param_dict[parameter_id]['value'], value)
        self.assertEqual(param_dict[parameter_id]['distribution'], distribution)

    def test_replace_initial_id(self):
        amr = _d(self.sir_amr)
        old_id = 'I'
        new_id = 'TEST'
        new_amr = replace_initial_id(amr, 'S', 'TEST')

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
        new_semantics_ode_observables = new_semantics_ode['observables']

        for new_state in new_model_states:
            self.assertNotEqual(removed_state_id, new_state['id'])

        for new_transition in new_model_transitions:
            self.assertNotIn(removed_state_id, new_transition['input'])
            self.assertNotIn(removed_state_id, new_transition['output'])

        # output rates that originally contained targeted state are removed
        # not sure if this is intended
        for new_rate in new_semantics_ode_rates:
            self.assertNotIn(removed_state_id, new_rate['expression'])
            self.assertNotIn(removed_state_id, new_rate['expression_mathml'])

        for new_initial in new_semantics_ode_initials:
            self.assertNotEqual(removed_state_id, new_initial['target'])

        # output observable expressions that originally contained targeted state still exist with targeted state removed
        # (e.g. 'S+R' -> 'R') if 'S' is the removed state
        for new_observable in new_semantics_ode_observables:
            self.assertNotIn(removed_state_id, new_observable['expression'])
            self.assertNotIn(removed_state_id, new_observable['expression_mathml'])

    @SBMLMATH_REQUIRED
    def test_add_state(self):
        amr = _d(self.sir_amr)
        new_state_id = 'TEST'
        new_state_display_name = 'TEST_DISPLAY_NAME'
        new_state_grounding_ido = '5555'
        context_str = 'TEST_CONTEXT'
        new_state_grounding = {'ido': new_state_grounding_ido}
        new_state_context = {'context_key': context_str}
        new_state_units = "<apply><times/><ci>E</ci><ci>delta</ci></apply>"
        initial_expression_xml = "<apply><times/><ci>beta</ci><ci>gamma</ci></apply>"

        new_amr = add_state(amr, state_id=new_state_id, name=new_state_display_name,
                            units_mathml=new_state_units, grounding=new_state_grounding,
                            context=new_state_context)

        state_dict = {}
        for state in new_amr['model']['states']:
            name = state.pop('id')
            state_dict[name] = state

        self.assertIn(new_state_id, state_dict)
        self.assertEqual(state_dict[new_state_id]['name'], new_state_display_name)
        self.assertEqual(state_dict[new_state_id]['grounding']['identifiers']['ido'], new_state_grounding_ido)
        self.assertEqual(state_dict[new_state_id]['grounding']['modifiers']['context_key'], context_str)
        self.assertEqual(state_dict[new_state_id]['units']['expression'], str(mathml_to_expression(new_state_units)))
        self.assertEqual(state_dict[new_state_id]['units']['expression_mathml'], new_state_units)

    def test_remove_transition(self):
        removed_transition = 'inf'
        amr = _d(self.sir_amr)

        new_amr = remove_transition(amr, removed_transition)
        new_model_transition = new_amr['model']['transitions']

        for new_transition in new_model_transition:
            self.assertNotEqual(removed_transition, new_transition['id'])

    @SBMLMATH_REQUIRED
    def test_add_transition(self):
        test_subject_concept_id = 'S'
        test_outcome_concept_id = 'I'
        expression_xml = "<apply><times/><ci>E</ci><ci>delta</ci></apply>"
        new_transition_id = 'test'

        old_natural_conversion_amr = _d(self.sir_amr)
        old_natural_production_amr = _d(self.sir_amr)
        old_natural_degradation_amr = _d(self.sir_amr)

        # NaturalConversion
        new_natural_conversion_amr = add_transition(old_natural_conversion_amr, new_transition_id,
                                                    rate_law_mathml=expression_xml,
                                                    src_id=test_subject_concept_id,
                                                    tgt_id=test_outcome_concept_id)

        natural_conversion_transition_dict = {}
        natural_conversion_rate_dict = {}
        natural_conversion_state_dict = {}

        for transition in new_natural_conversion_amr['model']['transitions']:
            name = transition.pop('id')
            natural_conversion_transition_dict[name] = transition

        for rate in new_natural_conversion_amr['semantics']['ode']['rates']:
            name = rate.pop('target')
            natural_conversion_rate_dict[name] = rate

        for state in new_natural_conversion_amr['model']['states']:
            name = state.pop('id')
            natural_conversion_state_dict[name] = state

        self.assertIn(new_transition_id, natural_conversion_transition_dict)
        self.assertIn(new_transition_id, natural_conversion_rate_dict)
        self.assertEqual(expression_xml, natural_conversion_rate_dict[new_transition_id]['expression_mathml'])
        self.assertEqual(str(mathml_to_expression(expression_xml)),
                         natural_conversion_rate_dict[new_transition_id]['expression'])
        self.assertIn(test_subject_concept_id, natural_conversion_state_dict)
        self.assertIn(test_outcome_concept_id, natural_conversion_state_dict)

        # NaturalProduction
        new_natural_production_amr = add_transition(old_natural_production_amr, new_transition_id,
                                                    rate_law_mathml=expression_xml,
                                                    tgt_id=test_outcome_concept_id)
        natural_production_transition_dict = {}
        natural_production_rate_dict = {}
        natural_production_state_dict = {}

        for transition in new_natural_production_amr['model']['transitions']:
            name = transition.pop('id')
            natural_production_transition_dict[name] = transition

        for rate in new_natural_production_amr['semantics']['ode']['rates']:
            name = rate.pop('target')
            natural_production_rate_dict[name] = rate

        for state in new_natural_production_amr['model']['states']:
            name = state.pop('id')
            natural_production_state_dict[name] = state

        self.assertIn(new_transition_id, natural_production_transition_dict)
        self.assertIn(new_transition_id, natural_production_rate_dict)
        self.assertEqual(expression_xml, natural_production_rate_dict[new_transition_id]['expression_mathml'])
        self.assertEqual(str(mathml_to_expression(expression_xml)),
                         natural_production_rate_dict[new_transition_id]['expression'])
        self.assertIn(test_outcome_concept_id, natural_production_state_dict)

        # NaturalDegradation
        new_natural_degradation_amr = add_transition(old_natural_degradation_amr, new_transition_id,
                                                     rate_law_mathml=expression_xml,
                                                     src_id=test_subject_concept_id)
        natural_degradation_transition_dict = {}
        natural_degradation_rate_dict = {}
        natural_degradation_state_dict = {}

        for transition in new_natural_degradation_amr['model']['transitions']:
            name = transition.pop('id')
            natural_degradation_transition_dict[name] = transition

        for rate in new_natural_degradation_amr['semantics']['ode']['rates']:
            name = rate.pop('target')
            natural_degradation_rate_dict[name] = rate

        for state in new_natural_degradation_amr['model']['states']:
            name = state.pop('id')
            natural_degradation_state_dict[name] = state

        self.assertIn(new_transition_id, natural_degradation_transition_dict)
        self.assertIn(new_transition_id, natural_degradation_rate_dict)
        self.assertEqual(expression_xml, natural_degradation_rate_dict[new_transition_id]['expression_mathml'])
        self.assertEqual(str(mathml_to_expression(expression_xml)),
                         natural_degradation_rate_dict[new_transition_id]['expression'])
        self.assertIn(test_subject_concept_id, natural_degradation_state_dict)

    @SBMLMATH_REQUIRED
    def test_add_transition_params_as_argument(self):
        test_subject_concept_id = 'S'
        test_outcome_concept_id = 'I'
        expression_xml = "<apply><times/><ci>E</ci><ci>delta</ci></apply>"
        new_transition_id = 'test'

        # Create a parameter dictionary that a user would have to create in this form if a user wants to add new
        # parameters from rate law expressions by passing in an argument to "add_transition"
        test_params_dict = {}
        parameter_id = 'delta'
        name = 'TEST_DISPLAY'
        description = 'TEST_DESCRIPTION'
        value = 0.35
        dist_type = 'test_dist'
        params = {parameter_id: value}
        distribution = {'type': dist_type,
                        'parameters': params}
        test_params_dict[parameter_id] = {
            'display_name': name,
            'description': description,
            'value': value,
            'distribution': distribution,
            'units': expression_xml
        }

        # Test to see if parameters with no attributes initialized are correctly added to parameters list of output amr
        empty_parameter_id = 'E'
        test_params_dict[empty_parameter_id] = {
            'display_name': None,
            'description': None,
            'value': None,
            'distribution': None,
            'units': None
        }

        old_natural_conversion_amr = _d(self.sir_amr)
        old_natural_production_amr = _d(self.sir_amr)
        old_natural_degradation_amr = _d(self.sir_amr)

        new_natural_conversion_amr = add_transition(old_natural_conversion_amr, new_transition_id,
                                                    rate_law_mathml=expression_xml,
                                                    src_id=test_subject_concept_id,
                                                    tgt_id=test_outcome_concept_id,
                                                    params_dict=test_params_dict)

        natural_conversion_param_dict = {}

        for param in new_natural_conversion_amr['semantics']['ode']['parameters']:
            popped_id = param.pop('id')
            natural_conversion_param_dict[popped_id] = param

        self.assertIn(parameter_id, natural_conversion_param_dict)
        self.assertIn(empty_parameter_id, natural_conversion_param_dict)
        self.assertEqual(value, natural_conversion_param_dict[parameter_id]['value'])
        self.assertEqual(name, natural_conversion_param_dict[parameter_id]['name'])
        self.assertEqual(description, natural_conversion_param_dict[parameter_id]['description'])
        # Compare sorted expression_mathml because cannot compare expression_mathml string directly due to
        # output amr expression is return of expression_to_mathml(mathml_to_expression(xml_string)) which switches
        # the terms around when compared to input xml_string (e.g. xml_string = '<ci><delta><ci><ci><beta><ci>',
        # expression_to_mathml(mathml_to_expression(xml_string)) = '<ci><beta<ci><ci><delta><ci>'

        self.assertEqual(sorted(expression_xml),
                         sorted(natural_conversion_param_dict[parameter_id]['units']['expression_mathml']))
        self.assertEqual(str(mathml_to_expression(expression_xml)),
                         natural_conversion_param_dict[parameter_id]['units']['expression'])
        self.assertEqual(distribution, natural_conversion_param_dict[parameter_id]['distribution'])

        # NaturalProduction
        new_natural_production_amr = add_transition(old_natural_production_amr, new_transition_id,
                                                    rate_law_mathml=expression_xml,
                                                    tgt_id=test_outcome_concept_id,
                                                    params_dict=test_params_dict)

        natural_production_param_dict = {}

        for param in new_natural_production_amr['semantics']['ode']['parameters']:
            popped_id = param.pop('id')
            natural_production_param_dict[popped_id] = param

        self.assertIn(parameter_id, natural_production_param_dict)
        self.assertIn(empty_parameter_id, natural_production_param_dict)
        self.assertEqual(value, natural_production_param_dict[parameter_id]['value'])
        self.assertEqual(name, natural_production_param_dict[parameter_id]['name'])
        self.assertEqual(description, natural_production_param_dict[parameter_id]['description'])
        self.assertEqual(sorted(expression_xml),
                         sorted(natural_production_param_dict[parameter_id]['units']['expression_mathml']))
        self.assertEqual(str(mathml_to_expression(expression_xml)),
                         natural_production_param_dict[parameter_id]['units']['expression'])
        self.assertEqual(distribution, natural_production_param_dict[parameter_id]['distribution'])

        # NaturalDegradation
        new_natural_degradation_amr = add_transition(old_natural_degradation_amr, new_transition_id,
                                                     rate_law_mathml=expression_xml,
                                                     src_id=test_subject_concept_id,
                                                     params_dict=test_params_dict)

        natural_degradation_param_dict = {}

        for param in new_natural_degradation_amr['semantics']['ode']['parameters']:
            popped_id = param.pop('id')
            natural_degradation_param_dict[popped_id] = param

        self.assertIn(parameter_id, natural_degradation_param_dict)
        self.assertIn(empty_parameter_id, natural_degradation_param_dict)
        self.assertEqual(value, natural_degradation_param_dict[parameter_id]['value'])
        self.assertEqual(name, natural_degradation_param_dict[parameter_id]['name'])
        self.assertEqual(description, natural_degradation_param_dict[parameter_id]['description'])
        self.assertEqual(sorted(expression_xml),
                         sorted(natural_degradation_param_dict[parameter_id]['units']['expression_mathml']))
        self.assertEqual(str(mathml_to_expression(expression_xml)),
                         natural_degradation_param_dict[parameter_id]['units']['expression'])
        self.assertEqual(distribution, natural_degradation_param_dict[parameter_id]['distribution'])

    @SBMLMATH_REQUIRED
    def test_add_transition_params_implicitly(self):
        test_subject_concept_id = 'S'
        test_outcome_concept_id = 'I'
        expression_xml = "<apply><times/><ci>sigma</ci><ci>delta</ci></apply>"
        new_transition_id = 'test'

        old_natural_conversion_amr = _d(self.sir_amr)
        old_natural_production_amr = _d(self.sir_amr)
        old_natural_degradation_amr = _d(self.sir_amr)

        new_natural_conversion_amr = add_transition(old_natural_conversion_amr, new_transition_id,
                                                    rate_law_mathml=expression_xml,
                                                    src_id=test_subject_concept_id,
                                                    tgt_id=test_outcome_concept_id)

        natural_conversion_param_dict = {}

        for param in new_natural_conversion_amr['semantics']['ode']['parameters']:
            name = param.pop('id')
            natural_conversion_param_dict[name] = param

        self.assertIn('delta', natural_conversion_param_dict)
        self.assertIn('sigma', natural_conversion_param_dict)

        new_natural_production_amr = add_transition(old_natural_production_amr, new_transition_id,
                                                    rate_law_mathml=expression_xml,
                                                    tgt_id=test_outcome_concept_id)
        natural_production_param_dict = {}
        for param in new_natural_production_amr['semantics']['ode']['parameters']:
            name = param.pop('id')
            natural_production_param_dict[name] = param

        self.assertIn('delta', natural_production_param_dict)
        self.assertIn('sigma', natural_production_param_dict)

        new_natural_degradation_amr = add_transition(old_natural_degradation_amr, new_transition_id,
                                                     rate_law_mathml=expression_xml,
                                                     src_id=test_subject_concept_id)
        natural_degradation_param_dict = {}
        for param in new_natural_degradation_amr['semantics']['ode']['parameters']:
            name = param.pop('id')
            natural_degradation_param_dict[name] = param

        self.assertIn('delta', natural_degradation_param_dict)
        self.assertIn('sigma', natural_degradation_param_dict)

    def test_add_transition_no_rate_law(self):
        test_subject_concept_id = 'S'
        test_outcome_concept_id = 'I'
        new_transition_id = 'test'
        old_natural_conversion_amr = _d(self.sir_amr)
        new_natural_conversion_amr = add_transition(old_natural_conversion_amr, new_transition_id,
                                                    src_id=test_subject_concept_id,
                                                    tgt_id=test_outcome_concept_id)
        natural_conversion_transition_dict = {}

        natural_conversion_state_dict = {}
        for transition in new_natural_conversion_amr['model']['transitions']:
            name = transition.pop('id')
            natural_conversion_transition_dict[name] = transition

        for state in new_natural_conversion_amr['model']['states']:
            name = state.pop('id')
            natural_conversion_state_dict[name] = state

        self.assertIn(new_transition_id, natural_conversion_transition_dict)
        self.assertIn(test_subject_concept_id, natural_conversion_state_dict)
        self.assertIn(test_outcome_concept_id, natural_conversion_state_dict)

    @SBMLMATH_REQUIRED
    def test_replace_rate_law_sympy(self):
        transition_id = 'inf'
        target_expression_xml_str = '<apply><plus/><ci>X</ci><cn>8</cn></apply>'
        target_expression_sympy = mathml_to_expression(target_expression_xml_str)

        amr = _d(self.sir_amr)
        new_amr = replace_rate_law_sympy(amr, transition_id, target_expression_sympy)
        new_semantics_ode_rates = new_amr['semantics']['ode']['rates']

        for new_rate in new_semantics_ode_rates:
            if new_rate['target'] == transition_id:
                self.assertEqual(str(target_expression_sympy), new_rate['expression'])
                self.assertEqual(target_expression_xml_str, new_rate['expression_mathml'])

    @SBMLMATH_REQUIRED
    def test_replace_rate_law_mathml(self):
        amr = _d(self.sir_amr)
        transition_id = 'inf'
        target_expression_xml_str = "<apply><times/><ci>E</ci><ci>delta</ci></apply>"
        target_expression_sympy = mathml_to_expression(target_expression_xml_str)

        new_amr = replace_rate_law_mathml(amr, transition_id, target_expression_xml_str)

        new_semantics_ode_rates = new_amr['semantics']['ode']['rates']

        for new_rate in new_semantics_ode_rates:
            if new_rate['target'] == transition_id:
                self.assertEqual(str(target_expression_sympy), new_rate['expression'])
                self.assertEqual(target_expression_xml_str, new_rate['expression_mathml'])

    @SBMLMATH_REQUIRED
    def test_replace_observable_expression_sympy(self):
        obs_id = 'noninf'
        amr = _d(self.sir_amr)
        target_expression_xml_str = "<apply><times/><ci>E</ci><ci>beta</ci></apply>"
        target_expression_sympy = mathml_to_expression(target_expression_xml_str)
        new_amr = replace_observable_expression_sympy(amr, obs_id, target_expression_sympy)

        for new_obs in new_amr['semantics']['ode']['observables']:
            if new_obs['id'] == obs_id:
                self.assertEqual(str(target_expression_sympy), new_obs['expression'])
                self.assertEqual(target_expression_xml_str, new_obs['expression_mathml'])

    @SBMLMATH_REQUIRED
    def test_replace_initial_expression_sympy(self):
        initial_id = 'S'
        amr = _d(self.sir_amr)
        target_expression_xml_str = "<apply><times/><ci>E</ci><ci>beta</ci></apply>"
        target_expression_sympy = mathml_to_expression(target_expression_xml_str)
        new_amr = replace_initial_expression_sympy(amr, initial_id, target_expression_sympy)

        for new_initial in new_amr['semantics']['ode']['initials']:
            if new_initial['target'] == initial_id:
                self.assertEqual(str(target_expression_sympy), new_initial['expression'])
                self.assertEqual(target_expression_xml_str, new_initial['expression_mathml'])

    @SBMLMATH_REQUIRED
    def test_replace_observable_expression_mathml(self):
        obs_id = 'noninf'
        amr = _d(self.sir_amr)
        target_expression_xml_str = "<apply><times/><ci>E</ci><ci>beta</ci></apply>"
        target_expression_sympy = mathml_to_expression(target_expression_xml_str)
        new_amr = replace_observable_expression_mathml(amr, obs_id, target_expression_xml_str)

        for new_obs in new_amr['semantics']['ode']['observables']:
            if new_obs['id'] == obs_id:
                self.assertEqual(str(target_expression_sympy), new_obs['expression'])
                self.assertEqual(target_expression_xml_str, new_obs['expression_mathml'])

    @SBMLMATH_REQUIRED
    def test_replace_initial_expression_mathml(self):
        initial_id = 'S'
        amr = _d(self.sir_amr)
        target_expression_xml_str = "<apply><times/><ci>E</ci><ci>beta</ci></apply>"
        target_expression_sympy = mathml_to_expression(target_expression_xml_str)
        new_amr = replace_initial_expression_mathml(amr, initial_id, target_expression_xml_str)

        for new_initial in new_amr['semantics']['ode']['initials']:
            if new_initial['target'] == initial_id:
                self.assertEqual(str(target_expression_sympy), new_initial['expression'])
                self.assertEqual(target_expression_xml_str, new_initial['expression_mathml'])

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

    def test_decapodes(self):
        data = requests.get(
            'https://raw.githubusercontent.com/ciemss/Decapodes.jl/'
            'sa_climate_modeling/examples/climate/ice_dynamics.json').json()
        # var_list = []
        # var_map = {}
        # for var in data['Var']:
        #     var_list.append(Variable(var['_id'], var['type'], var['name'], data['Op1'], data['Op2']))
        #     var_map[var['_id']] = var['name']

        variables = {var['_id']: Variable(var_id=var['_id'], type=var['type'], name=var['name'],
                                          op1_list=data['Op1'], op2_list=data['Op2']) for var in data['Var']}
        op1s = {op['_id']: Op1(src=variables[op['src']], tgt=variables[op['tgt']], op1=op['op1']) for op in data['Op1']}
        op2s = {op['_id']: Op2(proj1=variables[op['proj1']], proj2=variables[op['proj2']], res=variables[op['res']],
                               op2=op['op2']) for op in data['Op2']}

        # build up data structure mapping the outputs (targets) of Ops to the Ops they are produced by
        op1s_targets = {op.tgt: op_id for op_id, op in op1s.items()}
        op2s_targets = {op.res: op_id for op_id, op in op2s.items()}

        inputs = set()
        outputs = set()
        for op1 in op1s.values():
            inputs.add(op1.src)
            outputs.add(op1.tgt)
        for op2 in op2s.values():
            inputs.add(op2.proj1)
            inputs.add(op2.proj2)
            outputs.add(op2.res)

        # this finds set of varaibles that are only outputs and never inputs
        var_only_outputs = set(variables.values()) - inputs
        var_only_inputs = set(variables.values()) - outputs

        var_value_mapping = {var.variable_id: var.name for var in var_only_inputs}
        var_mapping_for_method = {var.variable_id: var.name for var in variables.values()}
        var_mapping_for_2nd_method = {var.variable_id: var for var in var_only_inputs}
        # while True:
        #     flag = False
        #     for op1 in op1s.values():
        #         if op1.src.variable_id in var_value_mapping:
        #             flag = True
        #             var_value_mapping[op1.tgt.variable_id] = 'variable:' + op1.src.name + '| operation:' + op1.op1 + '|'
        #
        #     if flag is False:
        #         break

        var = variables[19]
        #var.create_expression(var.variable_id, var_mapping_for_method)
        print()
