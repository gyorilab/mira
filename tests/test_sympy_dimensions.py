import pandas as pd
from sympy import mathml
from sympy.core.numbers import One
from sympy.physics.units.definitions.dimension_definitions import angle
from sympy.physics.units import (
    mass,
    kg,
    length,
    m,
    time,
    s,
    temperature,
    current,
)
from mira.sources.space_latex import (
    parse_sympy_dimensions,
    dimension_mapping,
    load_df_json,
    DIMENSION_COLUMN,
    get_unit_name,
    get_exponent,
    get_unit_names_exponents,
    unit_exponents_to_sympy_si,
    unit_exponents_to_mathml_si,
    unit_exponents_to_mathml_dim,
    unit_exponents_to_sympy_dim,
)


def test_base_units():
    for unit in ["-", "m", "s", "kg", "K", "A", "deg", "rad"]:
        parsed_name = get_unit_name(unit)
        parsed_exponent = get_exponent(unit)
        assert parsed_name == unit
        assert parsed_exponent == 1

        length_unit_list = get_unit_names_exponents(unit)
        assert len(length_unit_list) == 1
        assert length_unit_list[0] == (unit, 1)


def test_joules():
    joule_unit = r"\mathrm{kg} \cdot \mathrm{m}^2 \cdot \mathrm{s}^{-2}"
    parsed = parse_sympy_dimensions(joule_unit)
    joules = mass * length**2 * time**-2
    assert parsed == joules


def test_newtons():
    # Newton = mass * acceleration = mass * length * time ** -2
    newton_unit = r"\mathrm{kg} \cdot \mathrm{m} \cdot \mathrm{s}^{-2}"
    parsed = parse_sympy_dimensions(newton_unit)
    newtons = mass * length * time**-2
    assert parsed == newtons


def test_watts():
    # Watt = power = energy / time = mass * length ** 2 * time ** -3
    watt_unit = r"\mathrm{kg} \cdot \mathrm{m}^2 \cdot \mathrm{s}^{-3}"
    parsed = parse_sympy_dimensions(watt_unit)
    watts = mass * length**2 * time**-3
    assert parsed == watts


def test_tesla():
    # Tesla = magnetic flux density = magnetic flux / area = mass * length ** 2 * time ** -2 * current ** -1
    tesla_unit = r"\mathrm{kg} \cdot \mathrm{m}^2 \cdot \mathrm{s}^{-2} \cdot \mathrm{A}^{-1}"
    parsed = parse_sympy_dimensions(tesla_unit)
    tesla = mass * length**2 * time**-2 * current**-1
    assert parsed == tesla


def test_boltzmann_constant():
    # k_B = Boltzmann constant = 1.380649e-23 J/K
    # J/K = kg * m ** 2 * s ** -2 * K ** -1
    boltzmann_unit = r"\mathrm{kg} \cdot \mathrm{m}^2 \cdot \mathrm{s}^{-2} \cdot \mathrm{K}^{-1}"
    parsed = parse_sympy_dimensions(boltzmann_unit)
    boltzmann = mass * length**2 * time**-2 * temperature**-1
    assert parsed == boltzmann


def test_json_serialization():
    # Test that the parsed units can be serialized to JSON
    header = (
        "Symbol",
        "Type",
        "Name",
        "Description",
        "SI-Units",
        "Ref.",
    )
    data = [
        (
            r"$\rho$",
            "Variable",
            "rho",
            "mass density",
            r"$\mathrm{kg} \cdot \mathrm{m}^{3}$",
            "1",
        ),
        (
            r"$N_s$",
            "Variable",
            "",
            "Number Density of species s",
            r"$\mathrm{m}^{-3}$",
            "1",
        ),
        (
            r"$M_s$",
            "Variable",
            "",
            "Molecular mass of species s",
            "kg",
            "1",
        ),
        (
            r"$p$",
            "Variable",
            "",
            "Pressure",
            r"$\mathrm{kg} \cdot \mathrm{m}^{-1} \cdot \mathrm{s}^{-2}$",
            "2",
        ),
        (
            r"$\mathscr{T}$",
            "Variable",
            "",
            "Normalized Temperature",
            r"$\mathrm{m}^2 \cdot \mathrm{s}^{-2}$",
            "2",
        ),
    ]
    df = pd.DataFrame(data, columns=header).astype(dtype={"Ref.": str})

    # Add the sympy dimensions column
    df[DIMENSION_COLUMN] = df["SI-Units"].apply(parse_sympy_dimensions)

    # Dump to json
    df.to_json("test.json", orient="records", indent=2, default_handler=str)
    loaded_df = load_df_json("test.json")

    # Test equality for all but the sympy_dimensions column
    assert df.drop(columns=[DIMENSION_COLUMN]).equals(
        loaded_df.drop(columns=[DIMENSION_COLUMN])
    )

    # Test equality for the sympy_dimensions column by comparing the string representations
    assert (
        df[DIMENSION_COLUMN]
        .apply(str)
        .equals(loaded_df[DIMENSION_COLUMN].apply(str))
    )


def test_getting_unit_name():
    latex_str = r"$\mathrm{m}^{-2}$"
    unit_name = get_unit_name(latex_str)
    assert unit_name == "m"


def test_getting_exponent():
    latex_str = r"$\mathrm{m}^{-2}$"
    unit_power = get_exponent(latex_str)
    assert unit_power == -2


def test_getting_units_exponents():
    latex_str = r"$\mathrm{m}^{-2} \cdot \mathrm{kg} \cdot \mathrm{s}^{-2}$"
    units_exponents = get_unit_names_exponents(latex_str)
    assert set(units_exponents) == {("m", -2), ("kg", 1), ("s", -2)}


def test_unit_exponents_to_sympy_si():
    units_exponents = [("m", -2), ("kg", 1), ("s", -2)]
    sympy_si = unit_exponents_to_sympy_si(units_exponents)
    assert sympy_si == kg * m**-2 * s**-2


def test_unit_exponents_to_mathl_si():
    units_exponents = [("m", -2), ("kg", 1), ("s", -2)]
    mathml_si = unit_exponents_to_mathml_si(units_exponents)
    si_units = kg * m**-2 * s**-2
    assert mathml(si_units) == mathml_si


def test_unit_exponents_to_sympy_dim():
    units_exponents = [("m", -2), ("kg", 1), ("s", -2)]
    sympy_dimensions = unit_exponents_to_sympy_dim(units_exponents)
    # Check that the str representations are equal
    assert str(sympy_dimensions) == str(
        (mass * length**-2 * time**-2).args[0]
    )


def test_unit_exponents_to_mathml_dim():
    units_exponents = [("m", -2), ("kg", 1), ("s", -2)]
    mathml_dimensions = unit_exponents_to_mathml_dim(units_exponents)
    # Check that the str representations are equal
    assert mathml_dimensions == mathml(
        (mass * length**-2 * time**-2).args[0]
    )
