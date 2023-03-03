import pandas as pd
from sympy import mathml
from sympy.physics.units import (
    mass,
    kg,
    length,
    m,
    time,
    s,
)
from mira.sources.space_latex import (
    load_df_json,
    get_unit_name,
    get_exponent,
    get_unit_names_exponents,
    unit_exponents_to_sympy_si,
    unit_exponents_to_mathml_si,
    unit_exponents_to_mathml_dim,
    unit_exponents_to_sympy_dim,
    DIMENSION_COLUMN,
    SI_SYMPY_COLUMN,
    SI_MATHML_COLUMN,
    DIM_MATHML_COLUMN,
    column_mapping,
    dump_df_json,
    get_document_version_date,
    DATE_KEY,
    VERSION_KEY,
    get_shared_symbols,
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
    joule_latex = r"\mathrm{kg} \cdot \mathrm{m}^2 \cdot \mathrm{s}^{-2}"
    units_exponents_list = get_unit_names_exponents(joule_latex)
    assert len(units_exponents_list) == 3
    assert units_exponents_list[0] == ("kg", 1)
    assert units_exponents_list[1] == ("m", 2)
    assert units_exponents_list[2] == ("s", -2)

    joules_si = kg * m**2 * s**-2
    unit_exp_si = unit_exponents_to_sympy_si(units_exponents_list)
    assert joules_si == unit_exp_si

    mathml_si = mathml(joules_si)
    unit_exp_mathml_si = unit_exponents_to_mathml_si(units_exponents_list)
    assert mathml_si == unit_exp_mathml_si

    joules_dim = (mass * length**2 * time**-2).args[0]
    unit_exp_dim = unit_exponents_to_sympy_dim(units_exponents_list)
    assert joules_dim == unit_exp_dim

    mathml_dim = mathml(joules_dim)
    unit_exp_mathml_dim = unit_exponents_to_mathml_dim(units_exponents_list)
    assert mathml_dim == unit_exp_mathml_dim


def _get_test_df():
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
    df = pd.DataFrame(
        data, columns=[column_mapping.get(h, h) for h in header]
    ).astype(dtype={column_mapping["Ref."]: str})

    si_units_col_name = column_mapping["SI-Units"]
    # Add the sympy columns
    df[DIMENSION_COLUMN] = df[si_units_col_name].apply(
        lambda x: unit_exponents_to_sympy_dim(get_unit_names_exponents(x))
    )
    df[SI_SYMPY_COLUMN] = df[si_units_col_name].apply(
        lambda x: unit_exponents_to_sympy_si(get_unit_names_exponents(x))
    )
    df[SI_MATHML_COLUMN] = df[si_units_col_name].apply(
        lambda x: unit_exponents_to_mathml_si(get_unit_names_exponents(x))
    )
    df[DIM_MATHML_COLUMN] = df[si_units_col_name].apply(
        lambda x: unit_exponents_to_mathml_dim(get_unit_names_exponents(x))
    )
    return df


def test_json_serialization():
    df = _get_test_df()
    document_version = "0.1"
    date_str = "1/1/2020"

    # Dump to json
    dump_df_json(
        data_frame=df,
        path="test.json",
        document_version=document_version,
        date_str=date_str,
        default_handler=str,
    )
    loaded_df = load_df_json("test.json")
    assert loaded_df is not None
    assert VERSION_KEY in loaded_df.attrs
    assert DATE_KEY in loaded_df.attrs
    assert loaded_df.attrs[VERSION_KEY] == document_version
    assert loaded_df.attrs[DATE_KEY] == date_str

    # Test equality for all but the sympy_dimensions column
    assert df.drop(columns=[DIMENSION_COLUMN, SI_SYMPY_COLUMN]).equals(
        loaded_df.drop(columns=[DIMENSION_COLUMN, SI_SYMPY_COLUMN])
    )

    # Test equality for the sympy_dimensions column and si sympy column by
    # comparing the string representations
    assert (
        df[DIMENSION_COLUMN]
        .apply(str)
        .equals(loaded_df[DIMENSION_COLUMN].apply(str))
    )
    assert (
        df[SI_SYMPY_COLUMN]
        .apply(str)
        .equals(loaded_df[SI_SYMPY_COLUMN].apply(str))
    )


def test_getting_unit_name():
    latex_str = r"$\mathrm{m}^{-2}$"
    unit_name = get_unit_name(latex_str)
    assert unit_name == "m"


def test_getting_unit_name_bad_format():
    latex_str = r"$ m^{-2}$"
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


def test_getting_unit_exponents_bad_format():
    latex_str = r"$ m^{-2} \cdot \mathrm{kg} \cdot \mathrm{s}^{-2}$"
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


def test_get_date_version():
    raw_latex = r"""\maketitle

\noindent \textbf{Version}: v1.2 (2/21/2023)

"""
    version, date_str = get_document_version_date(raw_latex)
    assert date_str is not None
    assert date_str == "2/21/2023"
    assert version is not None
    assert version == "1.2"


def test_shared_symbols():
    model1_df = pd.DataFrame(
        {
            "symbol": [r"\rho", r"\beta", r"\alpha"],
            "name": ["Density", "Beta", "Alpha"],
            "description": ["Density", "Beta", "Alpha"],
        }
    )
    model2_df = pd.DataFrame(
        {
            "symbol": [r"\rho", r"\beta", r"\gamma"],
            "name": ["Density", "Beta", "Gamma"],
            "description": ["Density", "Beta", "Gamma"],
        }
    )
    shared_symbols = get_shared_symbols([model1_df, model2_df])
    assert shared_symbols.shape[0] == 4
    assert shared_symbols.shape[1] == 6
    assert set(shared_symbols.columns) == {
        "symbol",
        "name",
        "df_0",
        "df_1",
        "description_0",
        "description_1",
    }
    assert set(shared_symbols["symbol"]) == {
        r"\rho",
        r"\beta",
        r"\alpha",
        r"\gamma",
    }
    df0_col = "df_0"
    df1_col = "df_1"
    # Check that the entry for \rho is True for both models
    assert shared_symbols[shared_symbols["symbol"] == r"\rho"][df0_col].iloc[0]
    assert shared_symbols[shared_symbols["symbol"] == r"\rho"][df1_col].iloc[0]

    # Check that the entry for \alpha is False for df1 and True for df0
    assert not shared_symbols[shared_symbols["symbol"] == r"\alpha"][
        df1_col
    ].iloc[0]
    assert shared_symbols[shared_symbols["symbol"] == r"\alpha"][df0_col].iloc[
        0
    ]

    # Check that the entry for \gamma is False for df0 and True for df1
    assert not shared_symbols[shared_symbols["symbol"] == r"\gamma"][
        df0_col
    ].iloc[0]
    assert shared_symbols[shared_symbols["symbol"] == r"\gamma"][df1_col].iloc[
        0
    ]
