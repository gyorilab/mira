import json
import os
import re
import sys
from typing import List, Union, Tuple, Optional, Callable

import pandas as pd
import sympy
from matplotlib import pyplot as plt
from matplotlib_venn import venn3
from pandas import DataFrame
from sympy import mathml, Mul
from sympy.physics.units.definitions.dimension_definitions import (
    angle,
    mass,
    length,
    time,
    temperature,
    current,
)
from sympy.physics.units import (
    kg,
    m,
    s,
    K,
    A,
    Dimension,
    degree,
    radian,
)
from sympy.core.numbers import One

dimension_mapping = {
    "kg": mass,
    "g": mass,
    "m": length,
    "cm": length,
    "s": time,
    "K": temperature,
    "A": current,
    "-": One(),  # dimensionless
    "mol": One(),  # dimensionless
    "deg": angle,
    "degree": angle,
    "degrees": angle,
    "rad": angle,
    "radian": angle,
    "radians": angle,
    # SI derived units
    "C": current * time,
    "erg": mass * length**2 / time**2,
    "ergs": mass * length**2 / time**2,
    "J": mass * length**2 / time**2,
    "N": mass * length / time**2,
    "Pa": mass / length / time**2,
}
si_unit_mapping = {
    "kg": kg,
    "g": kg,
    "m": m,
    "cm": m,
    "s": s,
    "K": K,
    "A": A,
    "-": One(),  # dimensionless
    "mol": One(),  # dimensionless
    "deg": degree,
    "degree": degree,
    "degrees": degree,
    "rad": radian,
    "radian": radian,
    "radians": radian,
    # SI derived units
    "C": A * s,
    "erg": kg * m**2 / s**2,
    "ergs": kg * m**2 / s**2,
    "J": kg * m**2 / s**2,
    "N": kg * m / s**2,
    "Pa": kg / m / s**2,
}

# Symbol, Type, Name, Description, SI-Units, Ref.
column_mapping = {
    "Symbol": "symbol",
    "Type": "type",
    "Name": "name",
    "Description": "description",
    "Ref.": "equation_reference",
    "SI-Units": "si_units_latex",
}

DIMENSION_COLUMN = "dimensions_sympy"
SI_SYMPY_COLUMN = "si_sympy"
SI_MATHML_COLUMN = "si_mathml"
DIM_MATHML_COLUMN = "dimensions_mathml"
DF_DATA_KEY = "data"
VERSION_KEY = "version"
DATE_KEY = "date"


# Support for sympy Dimension when loading from json
def parse_sympy_dimension(sympy_str: Union[str, None]) -> Union[Mul, One, None]:
    # No units specified
    if sympy_str is None:
        return sympy_str
    # Has units specified or is an angle or is dimensionless==One
    elif sympy_str.startswith("Dimension("):
        dim = sympy.parse_expr(sympy_str)
        return dim.args[0]
    else:
        try:
            return sympy.parse_expr(sympy_str)
        except Exception as e:
            raise ValueError(
                f"Cannot parse {sympy_str} as a sympy Dimension, One, angle, or None"
            ) from e


def dump_df_json(
    path: str,
    data_frame: pd.DataFrame,
    default_handler: Callable,
    document_version: Optional[str] = None,
    date_str: Optional[str] = None,
    indent: int = 2,
):
    """Dump a DataFrame to a JSON file, including date and version information

    Parameters
    ----------
    path :
        A file path.
    data_frame :
        A DataFrame to serialize.
    default_handler :
        A function to handle non-serializable objects. Defaults to None.
    document_version :
        The version of the document.
    date_str :
        The date of the document.
    indent :
        The number of spaces to indent in the json file.
    """
    df_json = data_frame.to_dict(orient="records")
    attr_version = data_frame.attrs.get(VERSION_KEY, None) or document_version
    attr_date = data_frame.attrs.get(DATE_KEY, None) or date_str
    if attr_version is None:
        raise ValueError("No version specified for DataFrame")
    if attr_date is None:
        raise ValueError("No date specified for DataFrame")

    output = {
        VERSION_KEY: attr_version,
        DATE_KEY: attr_date,
        DF_DATA_KEY: df_json,
    }
    with open(path, "w") as fh:
        json.dump(output, fh, indent=indent, default=default_handler)


def load_df_json(path: str, **kwargs) -> DataFrame:
    """Load a DataFrame from a JSON file, handling sympy Dimensions correctly.

    Parameters
    ----------
    path :
        A file path.
    **kwargs
        Keyword arguments passed to json.load().

    Returns
    -------
    :
        A DataFrame deserialized from the JSON file.
    """
    # Load raw json
    with open(path, "r") as f:
        data = json.load(f, **kwargs)
    print(
        f"Loaded data from {path} with {len(data[DF_DATA_KEY])} variables "
        f"and version {data[VERSION_KEY]} dated {data[DATE_KEY]}"
    )
    df = pd.DataFrame(data[DF_DATA_KEY])
    # Setting the version and date as attributes
    if VERSION_KEY not in df.attrs:
        df.attrs[VERSION_KEY] = data[VERSION_KEY]
    if DATE_KEY not in df.attrs:
        df.attrs[DATE_KEY] = data[DATE_KEY]

    # Convert sympy strings to sympy expressions
    if DIMENSION_COLUMN in df.columns:
        df[DIMENSION_COLUMN] = df[DIMENSION_COLUMN].apply(parse_sympy_dimension)
    if SI_SYMPY_COLUMN in df.columns:
        df[SI_SYMPY_COLUMN] = df[SI_SYMPY_COLUMN].apply(parse_sympy_dimension)

    return df


def get_unit_name(latex_str: str) -> str:
    r"""Get the unit name from a latex string.

    Example input: $ \mathrm{s}^{-2}^{-1} $
    Example output: s

    Parameters
    ----------
    latex_str :
        A latex string.

    Returns
    -------
    :
        The unit name.
    """
    # Remove the $ at the beginning and end
    latex_str = latex_str.replace("$", "")

    # Check if \mathrm{...} is present
    if r"\mathrm" in latex_str or r"\textrm" in latex_str:
        # Get the unit name
        unit_name = re.search(r"\\mathrm\{(.+?)\}", latex_str)
        if unit_name is None:
            unit_name = re.search(r"\\textrm\{(.+?)\}", latex_str)

        if unit_name is None:
            raise ValueError(
                "Bad format for unit. '\\mathrm' found but no unit "
                "name found"
            )
        else:
            unit_name = unit_name.group(1)
    else:
        # No \mathrm{...} present, just a unit, e.g. "kg" or "m" or "m^{-1}"
        # Get the name but not the exponent
        if latex_str == "-":
            unit_name = "-"
        else:
            match = re.search(r"([a-zA-Z]+)\^?", latex_str)
            if match:
                unit_name = match.group(1)
            else:
                raise ValueError(
                    "Bad format for unit. No '\\mathrm' found and no unit "
                    "name found"
                )

    return unit_name


def get_exponent(latex_str: str) -> int:
    r"""Get the exponent from a latex string.

    Example input: $ \mathrm{s}^{-2} $
    Example output: -2

    Parameters
    ----------
    latex_str :
        A latex string.

    Returns
    -------
    :
        The exponent as an integer.
    """
    # Check for an exponent, e.g. ...^2 or ...^{-2} and get the value
    exponent = re.search(r"\^\{?(-?\d+)\}?", latex_str)
    if exponent:
        exponent = int(exponent.group(1))
    elif "^" in latex_str:
        # No exponent, but '^' is present
        raise ValueError(
            "Bad format for exponent: '^' found but no exponent found."
        )
    else:
        exponent = 1

    return exponent


def get_unit_names_exponents(latex_str: str) -> List[Tuple[str, int]]:
    r"""Get the units and exponents from a latex string.

    Example input: $ \mathrm{s}^{-2} \cdot \mathrm{m}^{-1} $
    Example output: [("s", -2), ("m", -1)]

    Parameters
    ----------
    latex_str :
        A latex string.

    Returns
    -------
    :
        A list of tuples of the form (unit, exponent).
    """
    # The input is a string of the form:
    # $ \mathrm{...} \cdot \mathrm{...}^{-<int>} ... $ OR just a single unit
    # e.g. kg or m or s without the mathmode $...$, find the units and parse
    # them into a sympy expression

    # Remove the $ at the beginning and end
    latex_str = latex_str.strip("$")

    if r"\cdot" in latex_str:
        # Split the string into the units
        units = latex_str.split(r"\cdot")
    else:
        units = [latex_str]

    # Strip whitespace
    units = [unit.strip() for unit in units]

    units_exponents = []
    for unit in units:
        if unit == "":
            raise ValueError("Empty unit")

        if unit == "-":
            # This is a dimensionless unit
            units_exponents.append((unit, 1))
        else:
            unit_name = get_unit_name(unit)
            exponent = get_exponent(unit)
            units_exponents.append((unit_name, exponent))

    return units_exponents


def parse_sympy_dimensions(latex_str: str) -> Union[Dimension, One]:
    # The input is a string of the form:
    # $ \mathrm{...} \cdot \mathrm{...}^{-<int>} ... $ OR just a single unit
    # e.g. kg or m or s without the mathmode $...$, find the units and parse
    # them into a sympy expression

    # Remove the $ at the beginning and end
    latex_str = latex_str.strip("$")

    if r"\cdot" in latex_str:
        # Split the string into the units
        units = latex_str.split(r"\cdot")
    else:
        units = [latex_str]

    # Strip whitespace
    units = [unit.strip() for unit in units]

    parsed = None
    for unit in units:
        if unit == "":
            raise ValueError("Empty unit")

        if unit == "-":
            # This is a dimensionless unit
            dim_unit = dimension_mapping[unit]

        else:
            # Get the exponent
            exponent = get_exponent(unit)

            # Strip off the exponent
            parsed_unit = re.sub(r"\^\{?(-?\d+)\}?", "", unit)

            # Get the unit name
            unit_name = get_unit_name(parsed_unit)

            assert unit_name in dimension_mapping, f"Unknown unit {unit_name}"

            dim_unit = dimension_mapping[unit_name] ** exponent

        if parsed is None:
            parsed = dim_unit
        else:
            parsed *= dim_unit
    return parsed


def unit_exponents_to_sympy_si(units_exps: List[Tuple[str, int]]):
    # Convert a sympy Dimension to a sympy expression in SI units
    # e.g. kg m^2 s^-2
    si_units = None
    for unit, exp in units_exps:
        if si_units is None:
            si_units = si_unit_mapping[unit] ** exp
        else:
            si_units *= si_unit_mapping[unit] ** exp

    return si_units


def unit_exponents_to_mathml_si(units_exps: List[Tuple[str, int]]) -> str:
    # Convert a sympy Dimension to a MathML in SI units
    si_units = unit_exponents_to_sympy_si(units_exps)
    return mathml(si_units)


def unit_exponents_to_sympy_dim(units_exps: List[Tuple[str, int]]):
    """Convert a list of units and exponents to dimensions

    Parameters
    ----------
    units_exps :
        A list of tuples of the form [(unit, exponent), ...]

    Returns
    -------
    :
        A multiplicative sympy expression containing the base dimensions of
        the units.
    """
    # Convert a sympy Dimension to a sympy expression in the base
    # dimensions e.g. m^2 kg s^-2 -> length**2 mass * time**-2
    sympy_dim = None
    for unit, exp in units_exps:
        if sympy_dim is None:
            sympy_dim = dimension_mapping[unit] ** exp
        else:
            sympy_dim *= dimension_mapping[unit] ** exp

    if isinstance(sympy_dim, One):
        return sympy.parse_expr("1")
    return sympy_dim.args[0]


def unit_exponents_to_mathml_dim(units_exps: List[Tuple[str, int]]) -> str:
    # Convert a sympy Dimension to a MathML
    sympy_dim = unit_exponents_to_sympy_dim(units_exps)
    return mathml(sympy_dim)


def parse_table(raw_latex_table: str) -> DataFrame:
    # Assume this is the text between \begin{tabular} and \end{tabular}
    # (or 'longtable')

    # Get the rows
    rows_iter = iter(raw_latex_table.split("\n"))

    # Find the header row, skip the table description, i.e. {|c|c|p{
    # 2cm}|...} and comments
    header_row = next(rows_iter)
    while header_row.strip().startswith(("%", "{", r"\hline")):
        header_row = next(rows_iter)

    assert "&" in header_row

    # Get the header: it contains LaTeX formatting, like \textbf{...}
    # Strip whitespace
    header = [
        t.replace(r"\\ \hline", "").strip() for t in header_row.split("&")
    ]
    # Remove \textbf{...}, \textit{...} and similar formatting
    header = [re.sub(r"\\textbf\{(.+?)\}", r"\1", t) for t in header]
    header = [re.sub(r"\\textit\{(.+?)\}", r"\1", t) for t in header]

    # map the header to the column names
    header = [column_mapping.get(h, h) for h in header]

    # Check if any of the header entries still contain LaTeX formatting
    # If so, raise an error
    for t in header:
        if re.search(r"\\text", t):
            raise ValueError(
                f"Header entry '{t}' still contains LaTeX formatting"
            )

    print("Found header:", header)

    # Parse the columns in the row:
    # Order: Symbol, Type, Name, Description, SI-Units, Ref.
    #   - The Symbol column contains LaTeX math
    #   - The symbol type column is either 'Variable', 'Constant', 'Index'.
    #     It may contain a question mark if the type is unclear.
    #   - The name column is empty 90% of time, but otherwise contains a
    #     suggested alternate name
    #   - The Description column contains a description of the symbol in
    #     plain text with the occasional inline, $...$, math.
    #   - The SI-Units column contain LaTeX math describing the
    #     physical units of the variable/constant in the SI system using any
    #     combination of kg, m, s, K, A, and - (for dimensionless quantities).
    #   - The Ref. column contains a latex reference to the equation in the
    #     paper where it was first seen. It's either of the form \ref{eqN} or
    #     \ref{sami_eqN} (N is the number of the equation). Get N.

    parsed_rows = []
    for row in rows_iter:
        # Skip comments
        if row.strip().startswith("%"):
            continue

        # Replace \& with 'and'
        row = row.replace(r"\&", "and")

        # Skip if row does not have correct number of columns
        columns = [c.replace(r"\\ \hline", "").strip() for c in row.split("&")]
        if len(columns) != len(header):
            if columns and columns[0] != r"\hline":
                print("Skipping row. Incorrect number of columns: ", columns)
                print("Original row:", row)

            continue

        # Get the equation number for the Ref. column (the last column)
        # Find the number in "eqN" or "sami_eqN"
        eq_num = re.search(r"eq(\d+)", columns[-1])
        if eq_num:
            eq_num = int(eq_num.group(1))
        else:
            eq_num = None
        columns[-1] = eq_num

        # Check if the SI-units column contains a bunch of question marks
        # (meaning there is a unit but it's not clear what it is)
        # '-' means it's unit-less
        # Extend the unit columns to include:
        #   - The LaTeX math for the units (original column)
        #   - The SI-units in sympy format (e.g. kg*m**2/s**2)
        #   - The dimensions in sympy format (e.g. mass*length**2/time**2) -
        #     this is currently what comes out of parse_sympy_units
        #   - The SI-units in mathml format
        #   - The dimensions in mathml format

        latex_si_units = columns[-2]
        if "?" in latex_si_units or latex_si_units is None:
            latex_si_units = None
            sympy_dimensions = None
            si_sympy = None
            si_mathml = None
            dim_mathml = None
        else:
            # Parse the units
            units_exps = get_unit_names_exponents(latex_si_units)
            sympy_dimensions = unit_exponents_to_sympy_dim(units_exps)
            dim_mathml = unit_exponents_to_mathml_dim(units_exps)
            si_sympy = unit_exponents_to_sympy_si(units_exps)
            si_mathml = unit_exponents_to_mathml_si(units_exps)

        columns[-2] = latex_si_units
        columns += [sympy_dimensions, si_sympy, si_mathml, dim_mathml]

        parsed_rows.append(columns)

    header += [
        DIMENSION_COLUMN,
        SI_SYMPY_COLUMN,
        SI_MATHML_COLUMN,
        DIM_MATHML_COLUMN,
    ]

    # Create the DataFrame
    df = DataFrame(parsed_rows, columns=header)
    return df


def parse_latex_tables(latex_file_path: str) -> List[DataFrame]:
    """Parse a string containing a LaTeX table into a pandas DataFrame."""
    # Read the file
    with open(latex_file_path, "r") as fh:
        raw_latex = fh.read()

    # Find all tables (also match 'longtable')
    table_tables = re.findall(
        r"\\begin{table}(.+?)\\end{table}", raw_latex, re.DOTALL
    )
    long_tables = re.findall(
        r"\\begin{longtable}(.+?)\\end{longtable}", raw_latex, re.DOTALL
    )
    tables = table_tables + long_tables

    # Parse each table
    dfs = []
    for table in tables:
        dfs.append(parse_table(table))

    return dfs


def get_shared_symbols(
    data_frames: List[DataFrame], names: List[str] = None
) -> DataFrame:
    """Find which symbols are present in which data frames"""
    # Do an outer join on all the data frames, matching on the symbol
    # column. Have the description column from each data frame tag along.
    out_df = data_frames[0]
    cols = ["symbol", "name", "description"]
    out_df = out_df[cols]
    for ix, df in enumerate(data_frames[1:], start=1):
        name = names[ix] if names else str(ix)
        out_df = out_df.merge(
            df[["symbol", "description"]],
            how="outer",
            on="symbol",
            suffixes=("", "_" + name),
        )

    # Rename the description column to description_0 for the first data frame
    out_df.rename(
        columns={"description": f"description_{names[0] if names else '0'}"},
        inplace=True,
    )

    # Set boolean columns for each data frame indicating whether the symbol
    # is present in that data frame or not
    for ix, df in enumerate(data_frames):
        name = names[ix] if names else str(ix)
        bool_col = f"df_{name}" if name.isnumeric() else name
        out_df[bool_col] = out_df[f"description_{name}"].notnull()
    return out_df


def get_document_version_date(
    raw_latex: str,
) -> Tuple[Union[str, None], Union[str, None]]:
    """Finds the version string from the main.tex file."""
    # Find the version string: v<Major>.<minor> (MM/DD/YYYY)
    # and extract version and date
    version_date = re.search(r"v(\d+\.\d+) \((\d+/\d+/\d+)\)", raw_latex)
    if version_date:
        vers = version_date.group(1)
        dt = version_date.group(2)
    else:
        vers = None
        dt = None

    return vers, dt


def get_all_symbols(df_list) -> DataFrame:
    # Merge all the data frames into one flattened data frame
    # only keep the following columns:
    #   - symbol
    #   - name
    #   - description
    #   - DIMENSION_COLUMN = "dimensions_sympy"
    #   - SI_SYMPY_COLUMN = "si_sympy"
    #   - SI_MATHML_COLUMN = "si_mathml"
    #   - DIM_MATHML_COLUMN = "dimensions_mathml"
    df_out = pd.concat(df_list, ignore_index=True)
    df_out = df_out[
        [
            "symbol",
            "name",
            "description",
            DIMENSION_COLUMN,
            SI_SYMPY_COLUMN,
            SI_MATHML_COLUMN,
            DIM_MATHML_COLUMN,
        ]
    ]

    return df_out


if __name__ == "__main__":
    if len(sys.argv) > 1:
        base_path = sys.argv[1]
    else:
        base_path = "."
    main_tex = os.path.join(base_path, "main.tex")
    version, date = get_document_version_date(open(main_tex, "r").read())
    if version is None or date is None:
        raise ValueError("Could not find version and date in main.tex")

    models = ["gitm", "sami", "tiegcm"]
    model_df_list = []
    for model_name in models:
        # Parse the tables in the LaTeX file
        model_tables = parse_latex_tables(
            os.path.join(base_path, f"{model_name}.tex")
        )
        assert len(model_tables) == 1

        # Save the tables as json files
        outfile = os.path.join(base_path, f"{model_name}_variables.json")
        dump_df_json(
            path=outfile,
            data_frame=model_tables[0],
            document_version=version,
            date_str=date,
            indent=2,
            default_handler=str,
        )
        model_df_list.append(model_tables[0])
        print(f"Got model {model_name} with {len(model_tables[0])} variables")

    # Merge the symbol columns from the two models in an outer join where
    # the resulting Nx2 DataFrame has boolean columns indicating whether
    # the symbol was found in each model.
    shared_symbols = get_shared_symbols(model_df_list, names=models)
    shared_symbols.to_csv(
        os.path.join(base_path, "shared_symbols.tsv"), index=False, sep="\t"
    )

    # Get all symbols from all the models in a flattened DataFrame
    all_symbols_df = get_all_symbols(model_df_list)

    # Save the flattened DataFrame as a tsv file
    all_symbols_df.to_csv(
        os.path.join(base_path, "all_symbols.tsv"), index=False, sep="\t"
    )

    # Plot a three-way Venn diagram of the shared symbols
    # 1: gitm, 2: sami, 3: tiegcm
    gitm_count = shared_symbols.query("gitm").shape[0]
    sami_count = shared_symbols.query("sami").shape[0]
    gitm_sami_count = shared_symbols.query("gitm & sami").shape[0]
    tiegcm_count = shared_symbols.query("tiegcm").shape[0]
    gitm_tiegcm_count = shared_symbols.query("gitm & tiegcm").shape[0]
    sami_tiegcm_count = shared_symbols.query("sami & tiegcm").shape[0]
    all_count = shared_symbols.query("gitm & tiegcm & sami").shape[0]

    fig, ax = plt.subplots()
    venn3(
        # A list (or a tuple) with 7 numbers, denoting the sizes of the regions in the following order:
        #        (100, 010, 110, 001, 101, 011, 111).
        subsets=(
            gitm_count,
            sami_count,
            gitm_sami_count,
            tiegcm_count,
            gitm_tiegcm_count,
            sami_tiegcm_count,
            all_count,
        ),
        set_labels=models,
        ax=ax,
    )
    fig.savefig(os.path.join(base_path, "shared_symbols_venn.png"))

    # plot 3-way venn diagram of the shared names
    gitm_names = set(model_df_list[0]["name"].str.lower())
    sami_names = set(model_df_list[1]["name"].str.lower())
    tiegcm_names = set(model_df_list[2]["name"].str.lower())

    fig, ax = plt.subplots()
    venn3(
        subsets=(gitm_names, sami_names, tiegcm_names),
        set_labels=models,
        ax=ax,
    )
    fig.savefig(os.path.join(base_path, "shared_names_venn.png"))
