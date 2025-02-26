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
    for model_id in BIOMODELS:
        tm_from_biomodel = get_template_model(model_id)
        sbml_string = template_model_to_sbml_string(tm_from_biomodel)
        reingested_tm = template_model_from_sbml_string(sbml_string)

        assert len(tm_from_biomodel.templates) == len(reingested_tm.templates)
        for biomodel_template, reingested_template in zip(
            tm_from_biomodel.templates, reingested_tm.templates
        ):
            # Cannot test for rate law equality because check fails on
            # Exposed*kappa*(-rho1 - rho2 + 1.0) == Exposed*kappa*(-rho1 - rho2 + 1)
            for concept_key in biomodel_template.concept_keys:
                # test to see if it's a list of concepts
                if concept_key[-1].lower() == "s":
                    biomodel_template_concepts = getattr(
                        biomodel_template, concept_key
                    )
                    reingested_template_concepts = getattr(
                        reingested_template, concept_key
                    )
                    # concept order is preserved
                    for biomodel_concept, reingested_concept in zip(
                        biomodel_template_concepts, reingested_template_concepts
                    ):
                        assert biomodel_concept.name == reingested_concept.name

                        # Remove artificial identifier generated from ingestion for
                        # non-mapped sbml models
                        if "biomodels.species" in biomodel_concept.identifiers:
                            biomodel_concept.identifiers.pop(
                                "biomodels.species"
                            )
                        if (
                            "biomodels.species"
                            in reingested_concept.identifiers
                        ):
                            reingested_concept.identifiers.pop(
                                "biomodels.species"
                            )
                        assert (
                            biomodel_concept.identifiers
                            == reingested_concept.identifiers
                        )
                        # If ingesting a non-mapped SBML model, the contexts names arbitrarily have "property" pre-pended

                        assert set(biomodel_concept.context.values()) == set(
                            reingested_concept.context.values()
                        )
                        assert (
                            biomodel_concept.units == reingested_concept.units
                        )

                else:
                    # single concept
                    biomodel_concept = getattr(biomodel_template, concept_key)
                    reingested_concept = getattr(
                        reingested_template, concept_key
                    )
                    assert biomodel_concept.name == reingested_concept.name
                    if "biomodels.species" in biomodel_concept.identifiers:
                        biomodel_concept.identifiers.pop("biomodels.species")
                    if "biomodels.species" in reingested_concept.identifiers:
                        reingested_concept.identifiers.pop("biomodels.species")
                    assert (
                        biomodel_concept.identifiers
                        == reingested_concept.identifiers
                    )
                    assert set(biomodel_concept.context.values()) == set(
                        reingested_concept.context.values()
                    )
                    assert biomodel_concept.units == reingested_concept.units

        # parameter, initial order isn't preserved
        # An extra parameter is generated in the re-ingested template model because
        # add the default compartment as a parameter
        assert (
            len(tm_from_biomodel.parameters)
            == len(reingested_tm.parameters) - 1
        )

        for parameter_id, parameter in tm_from_biomodel.parameters.items():
            assert parameter_id in reingested_tm.parameters
            reingested_parameter = reingested_tm.parameters.get(parameter_id)
            assert parameter.value == reingested_parameter.value
            assert parameter.units == reingested_parameter.units

        assert len(tm_from_biomodel.initials) == len(reingested_tm.initials)
        for initial_id, initial in tm_from_biomodel.initials.items():
            assert initial_id in reingested_tm.initials
            reingested_initial = reingested_tm.initials.get(initial_id)
            assert initial.expression == reingested_initial.expression
        assert len(tm_from_biomodel.get_concepts_name_map()) == len(
            reingested_tm.get_concepts_name_map()
        )

        biomodel_annots = tm_from_biomodel.annotations
        reingested_annots = reingested_tm.annotations

        assert biomodel_annots.name == reingested_annots.name
        assert biomodel_annots.description == reingested_annots.description
        assert set(author.name for author in biomodel_annots.authors) == set(
            author.name for author in reingested_annots.authors
        )
        assert set(biomodel_annots.diseases) == set(reingested_annots.diseases)
        assert set(biomodel_annots.pathogens) == set(
            reingested_annots.pathogens
        )
        assert set(biomodel_annots.hosts) == set(reingested_annots.hosts)
        assert set(biomodel_annots.references) == set(
            reingested_annots.references
        )
