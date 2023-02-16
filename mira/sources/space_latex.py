import re
from typing import List, Union

import pandas as pd
import sympy
from pandas import DataFrame
from sympy.physics.units.definitions.dimension_definitions import angle
from sympy.physics.units import (
    mass,
    length,
    time,
    temperature,
    current,
    Dimension,
)
from sympy.core.numbers import One

dimension_mapping = {
    "kg": mass,
    "m": length,
    "s": time,
    "K": temperature,
    "A": current,
    "-": One(),  # dimensionless
    "deg": angle,
    "degree": angle,
    "degrees": angle,
    "rad": angle,
    "radian": angle,
    "radians": angle,
}
DIMENSION_COLUMN = "sympy_dimensions"


# Support for sympy Dimension when loading from json
def parse_sympy_dimension(s: Union[str, None]) -> Union[Dimension, One, None]:
    # No units specified
    if s is None:
        return s
    # Has units specified or is an angle or is dimensionless==One
    elif s.startswith("Dimension(") or s == "One()" or s == "angle":
        return sympy.parse_expr(s)
    else:
        raise ValueError(f"Cannot parse {s} as a sympy Dimension, One, angle, or None")


def load_df_json(path_or_buf, **kwargs) -> DataFrame:
    """Load a DataFrame from a JSON file, handling sympy Dimensions correctly.

    Parameters
    ----------
    path_or_buf : str or Path
        A file path.
    **kwargs
        Keyword arguments passed to pandas.read_json.

    Returns
    -------
    :
        A DataFrame deserialized from the JSON file.
    """
    df = pd.read_json(path_or_buf, **kwargs, dtype={"Ref.": str})
    if DIMENSION_COLUMN not in df.columns:
        print("No sympy_dimensions column found, returning DataFrame")
        return df
    df[DIMENSION_COLUMN] = df[DIMENSION_COLUMN].apply(
        parse_sympy_dimension)
    return df


def parse_sympy_units(latex_str: str) -> Union[Dimension, One]:
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
            # Check for an exponent, e.g. ...^2 or ...^{-2} and get the value
            exponent = re.search(r"\^\{?(-?\d+)\}?", unit)
            if exponent:
                exponent = int(exponent.group(1))
            elif "^" in unit:
                # No exponent, but a ^ is present
                raise ValueError(
                    "Bad format for exponent. '^' found but no exponent found"
                )
            else:
                exponent = 1

            # Strip off the exponent
            parsed_unit = re.sub(r"\^\{?(-?\d+)\}?", "", unit)

            # Check if \mathrm{...} is present and if it has an exponent
            if r"\mathrm" in parsed_unit or r"\textrm" in parsed_unit:
                # Get the unit name
                unit_name = re.search(r"\\mathrm\{(.+?)\}", parsed_unit)
                if unit_name is None:
                    unit_name = re.search(r"\\textrm\{(.+?)\}", parsed_unit)

                if unit_name is None:
                    raise ValueError(
                        "Bad format for unit. '\\mathrm' found but no unit "
                        "name found"
                    )
                else:
                    unit_name = unit_name.group(1)
            else:
                # No \mathrm{...} present, just a unit
                unit_name = parsed_unit.strip()

            assert unit_name in dimension_mapping, f"Unknown unit {unit_name}"

            dim_unit = dimension_mapping[unit_name] ** exponent

        if parsed is None:
            parsed = dim_unit
        else:
            parsed *= dim_unit
    return parsed


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
    #   plain text with the occasional inline, $...$, math.
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
        # '-' means it's unitless
        si_units = columns[-2]
        if "?" in si_units:
            si_units = None
            sympy_dimensions = None
        else:
            sympy_dimensions = parse_sympy_units(si_units)
            pass

        columns[-2] = si_units
        columns.append(sympy_dimensions)

        parsed_rows.append(columns)

    header.append(DIMENSION_COLUMN)

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


if __name__ == "__main__":
    # Parse the tables in the LaTeX file
    gitm, sami2 = parse_latex_tables("./main.tex")

    # Save the tables as json files, drop the sympy dimensions column first
    gitm.to_json(
        "gitm_variables.json",
        orient="records",
        indent=2,
        default_handler=str,
    )
    sami2.drop("sympy_dimensions", axis=1).to_json(
        "sami2_variables.json",
        orient="records",
        indent=2,
        default_handler=str,

    )
