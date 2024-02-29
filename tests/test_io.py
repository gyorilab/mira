"""Test for metamodel io operations."""
import tempfile

from mira.metamodel import *

# List all templates classes
template_cls_list = Template.__subclasses__()

# Create Concepts for testing
controller1 = Concept(name="controller1")
controller2 = Concept(name="controller2")
subject = Concept(name="subject1")
outcome = Concept(name="outcome1")


def _check_roundtrip(tm: TemplateModel):
    # Test json serialization and deserialization

    # Get a temporary file
    with tempfile.NamedTemporaryFile(suffix=".json") as temp_file:
        # Write the model to the file
        model_to_json_file(tm, temp_file.name)
        # Read the model from the file
        tm2 = model_from_json_file(temp_file.name)
        # Check that the models are the same
        for t1, t2 in zip(tm.templates, tm2.templates):
            assert t1.is_equal_to(t2)


def test_templates():
    failed = []
    for templ_cls in template_cls_list:
        # Create the template
        template = templ_cls(
            # As long as the BaseModel is allowed to accept unused
            # arguments, we can pass all the arguments to the constructor.
            # The unused arguments will be ignored.
            controller=controller1,
            subject=subject,
            outcome=outcome,
            controllers=[controller1, controller2]
        )
        # Create the template model
        tm = TemplateModel(templates=[template])
        # Check the roundtrip
        try:
            _check_roundtrip(tm)
        except Exception as e:
            failed.append((templ_cls, str(e)))
    if failed:
        print(f"{len(failed)} roundtrips failed")
        for f in failed:
            print(f)
        raise AssertionError(f"{len(failed)} roundtrips failed")
