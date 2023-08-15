import json
import tempfile

import jsonschema
import requests
import sympy

from mira.examples.sir import sir_parameterized
from mira.metamodel import *
from mira.modeling import Model
from mira.modeling.askenet.petrinet import AskeNetPetriNetModel
from mira.sources.askenet.petrinet import template_model_from_askenet_json, model_from_url


def test_export():
    pm = AskeNetPetriNetModel(Model(sir_parameterized))

    # Test the json export
    _ = pm.to_json()

    # Test the json file export
    with tempfile.NamedTemporaryFile(suffix=".json") as temp_file:
        pm.to_json_file(
            temp_file.name,
            name='temp_aske_petrinet',
            description="A temporary petrinet",
            indent=2,
        )
        with open(temp_file.name, "r") as f:
            json_data = json.load(f)

    # Test the schema
    schema_url = json_data['schema']
    print(f"Schema URL: {schema_url}")
    remote_schema = requests.get(schema_url).json()
    try:
        jsonschema.validate(json_data, remote_schema)
    except jsonschema.ValidationError as e:
        raise jsonschema.ValidationError(
            "Validation of the exported JSON failed. Is the schema version "
            "correct?"
        ) from e

    # Test the pydanctic export
    pm.to_pydantic()

    # Get the template model
    tm = template_model_from_askenet_json(pm.to_json())

    # Test parameters
    assert 'beta' in tm.parameters
    assert tm.parameters['beta'].value == 0.1
    assert 'gamma' in tm.parameters
    assert tm.parameters['gamma'].value == 0.2

    # Test transitions
    c1, c2 = sorted([t for t in tm.templates], key=lambda s: s.__class__.__name__)
    assert isinstance(c1, ControlledConversion)
    assert c1.subject.name == "susceptible_population"
    assert 'ido' in c1.subject.identifiers
    assert c1.subject.identifiers['ido'] == '0000514'

    assert isinstance(c2, NaturalConversion)

    # Test initials
    assert 'susceptible_population' in tm.initials
    assert tm.initials['susceptible_population'].value == 1
    assert tm.initials['susceptible_population'].concept.name == \
           "susceptible_population"
    assert 'ido' in tm.initials['susceptible_population'].concept.identifiers
    assert tm.initials['susceptible_population'].concept.identifiers['ido'] \
           == '0000514'
    assert len(tm.templates) == 2


def test_validate_example():
    model_url = ('https://raw.githubusercontent.com/DARPA-ASKEM/'
                 'Model-Representations/main/petrinet/examples/sir.json')
    schema_url = ('https://raw.githubusercontent.com/DARPA-ASKEM/'
                  'Model-Representations/main/petrinet/petrinet_schema.json')
    model = model_from_url(model_url)
    assert len(model.templates) == 2
    assert model.observables
    assert model.time.name == 't'
    pm = AskeNetPetriNetModel(Model(model))
    remote_schema = requests.get(schema_url).json()

    # Test the json file export
    with tempfile.NamedTemporaryFile(suffix=".json") as temp_file:
        pm.to_json_file(
            temp_file.name,
            name='temp_aske_petrinet',
            description="A temporary petrinet",
            indent=2,
        )
        with open(temp_file.name, "r") as f:
            json_data = json.load(f)

    try:
        jsonschema.validate(json_data, remote_schema)
    except jsonschema.ValidationError as e:
        raise jsonschema.ValidationError(
            "Validation of the exported JSON failed. Is the schema version "
            "correct?"
        ) from e


def test_static_states():
    model_url = ('https://raw.githubusercontent.com/DARPA-ASKEM/'
                 'Model-Representations/main/petrinet/examples/sir.json')
    model_json = requests.get(model_url).json()
    model_json['model']['states'].append(
        {
            "id": "X",
            "name": "Isolated",
            "description": "Individuals that don't interact with anyone",
            "grounding": {
                "identifiers": {
                    "ido": "12345"
                }
            },
            "units": {
                "expression": "person",
                "expression_mathml": "<ci>person</ci>"
            }
        }
    )
    tm = template_model_from_askenet_json(model_json)
    assert len(tm.templates) == 3
    assert isinstance(tm.templates[-1], StaticConcept)
    assert tm.templates[-1].subject.name == 'X'
    model = Model(tm)
    assert ('X', ('identity', 'ido:12345')) in model.variables
    am = AskeNetPetriNetModel(model)
    aj = am.to_json()
    assert len(aj['model']['states']) == 4
    assert aj['model']['states'][-1]['id'] == 'X'


def test_lambda():
    """Make sure we can go end-to-end and correctly represent lambda as a parameter"""
    amr_model = {
        'name': 'Model',
        'schema': 'https://raw.githubusercontent.com/DARPA-ASKEM/Model-Representations/petrinet_v0.5/petrinet/petrinet_schema.json',
        'schema_name': 'petrinet',
        'model': {'states': [{'id': 'S',
                           'name': 'S',
                           'grounding': {'identifiers': {}, 'modifiers': {}}}],
               'transitions': [{'id': 't1',
                                'input': ['S'],
                                'output': [],
                                'properties': {'name': 't1'}}]},
        'semantics': {'ode': {'rates': [{'target': 't1',
                                      'expression': 'S*lambda',
                                      'expression_mathml': '<apply><times/><ci>S</ci><ci>lambda</ci></apply>'}],
                           'initials': [],
                           'parameters': [{'id': 'lambda', 'value': 0.1}],
                           'observables': [],
                           'time': {'id': 't'}}}
        }

    tm = template_model_from_askenet_json(amr_model)
    assert 'lambda' in tm.parameters
    assert list(tm.get_parameters_from_rate_law(
        tm.templates[0].rate_law))[0] == 'lambda'
    model = Model(tm)
    assert 'lambda' in model.parameters
    am = AskeNetPetriNetModel(model)
    aj = am.to_json()
    assert aj['semantics']['ode']['parameters'][0]['id'] == 'lambda'
    assert aj['semantics']['ode']['rates'][0]['expression'] == 'S*lambda'
