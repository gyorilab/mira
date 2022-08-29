from pathlib import Path
from dataclasses import asdict
from mira.modeling.gromet_model import GroMEtModel, model_to_gromet_json_file, model_to_gromet
from mira.metamodel import ControlledConversion, Concept, NaturalConversion
from mira.modeling import Model, TemplateModel


def _get_sir_model_templ():
    infected = Concept(name="infected population", identifiers={"ido": "0000511"})
    susceptible = Concept(name="susceptible population", identifiers={"ido": "0000514"})
    immune = Concept(name="immune population", identifiers={"ido": "0000592"})

    t1 = ControlledConversion(
        controller=infected,
        subject=susceptible,
        outcome=infected,
    )
    t2 = NaturalConversion(subject=infected, outcome=immune)
    sir_model_templ = TemplateModel(templates=[t1, t2])
    return sir_model_templ


def test_init():
    # Sanity check to see that the class can be instantiated
    sir_model_templ = _get_sir_model_templ()
    sir_model = Model(sir_model_templ)
    gromet_model = GroMEtModel(sir_model, "sir_model", "PetriNet")


def test_gromet_as_dict():
    sir_model_templ = _get_sir_model_templ()
    sir_model = Model(sir_model_templ)

    name = "sir_model"
    model_name = "PetriNet"

    gromet = model_to_gromet(sir_model, name=name, model_name=model_name)
    gromet_dict = asdict(gromet)


def test_gromet_json_conversion():
    """Test model_to_gromet_json_file and gromet_json_file_to_model"""
    sir_model_templ = _get_sir_model_templ()
    sir_model = Model(sir_model_templ)

    # Gromet json file
    fname = "sir_model_test.json"
    name = "sir_model"
    model_name = "PetriNet"
    model_to_gromet_json_file(model=sir_model, fname=fname, name=name, model_name=model_name)
    assert Path(fname).exists()
    assert Path(fname).stat().st_size > 0


def test_gromet_export():
    """Test that the produced gromet makes sense"""
    sir_model_template = _get_sir_model_templ()
    sir_model = Model(sir_model_template)
    gromet_export = GroMEtModel(sir_model, name="sir_model", model_name="PetriNet")

    gromet = gromet_export.gromet_model

    assert all(j.value is not None for j in gromet.junctions)

    # Test number of rates, S->I, I->R => 2
    nrates = len([j for j in gromet.junctions if j.type == "Rate"])
    ntrans = len(sir_model.transitions)
    assert nrates == ntrans, f"Expected {ntrans} rates, got {nrates}"

    # Test number of variables, S, I and R => 3
    nvars = len([j for j in gromet.junctions if j.type == "Variable"])
    true_nvars = len(sir_model.variables)
    assert nvars == true_nvars, f"Expected {true_nvars} variables, got {nvars}"

    # Number of wires: (1 incoming + 1 outgoing) per rate * two rates = 4
    nwires = len([w for w in gromet.wires])
    assert nwires == ntrans * nrates, f"Expected {ntrans} wires, got {nwires}"

    # Check for uniqueness
    n_unique_junctions = len(set(j.uid for j in gromet.junctions))
    n_junctions = len([j for j in gromet.junctions])
    assert (
        n_unique_junctions == n_junctions
    ), f"Expected {n_junctions} unique junctions, got {n_unique_junctions}"

    n_unique_wires = len(set(w.uid for w in gromet.wires))
    n_wires = len([w for w in gromet.wires])
    assert n_wires == n_unique_wires, f"Expected {n_wires} unique wires, got {n_unique_wires}"
