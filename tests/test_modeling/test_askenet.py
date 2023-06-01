import json
import tempfile

import jsonschema
import requests

from mira.examples.sir import sir_parameterized
from mira.metamodel import *
from mira.modeling import Model
from mira.modeling.askenet.petrinet import AskeNetPetriNetModel
from mira.sources.askenet.petrinet import template_model_from_askenet_json


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
