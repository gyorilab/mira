"""Tests to see if we can export SBML models from intermediate TemplateModels
 correctly while preserving a majority of the information stored in the
 TemplateModel."""
from mira.sources.biomodels import get_template_model
from mira.sources.sbml import template_model_from_sbml_string
from mira.modeling.sbml import template_model_to_sbml_string

BIOMODELS = [
    "BIOMD0000000955",
    "BIOMD0000000956",
    "BIOMD0000000957",
    "BIOMD0000000958",
    "BIOMD0000000960",
]


def test_sbml_export():
    for id in BIOMODELS:
        tm0 = get_template_model(id)
        s = template_model_to_sbml_string(tm0)
        tm1 = template_model_from_sbml_string(s)
        assert len(tm0.templates) == len(tm1.templates)
        for template0, template1 in zip(tm0.templates, tm1.templates):
            assert template0.type == template1.type

        # parameter, initial order isn't preserved
        # An extra parameter is generated in the re-ingested template model because
        # add the default compartment as a parameter
        assert len(tm0.parameters) == len(tm1.parameters) - 1
        assert len(tm0.initials) == len(tm1.initials)
        assert len(tm0.get_concepts_name_map()) == len(tm1.get_concepts_name_map())
