from pathlib import Path
from typing import List

import click
import pandas as pd
from mira.dkg.askemo.api import Term, write, HERE

header_row = 1
row_count = 59
google_sheet_csv_export_url = os.environ["SPACE_ONTOLOGY_URL"]
columns = list(range(11))


def read_google_sheet(
    url: str = google_sheet_csv_export_url,
    header: int = header_row,
    nrows: int = row_count,
    usecols: List[int] = None,
) -> pd.DataFrame:
    """Read the google sheet csv export into a pandas dataframe.

    Set empty cells to empty string instead of NaN.
    """
    if usecols is None:
        usecols = columns
    return pd.read_csv(
        url,
        header=header,
        nrows=nrows,
        usecols=usecols,
        na_filter=False,
        dtype=str,
    )


def export_to_json(sheet_df: pd.DataFrame, path: str = None):
    # DataFrame columns:
    # 'symbol',
    # 'ASKEMOSW',
    # 'name',
    # 'parent ASKEMOSW',
    # 'suggested grounding',
    # 'grounded name',
    # 'Link to grounding',
    # 'description',
    # 'example usage',
    # 'xrefs'

    # Output should roughly follow this format:
    #   [{
    #     "description": "The number of people who live in an area being modeled.",
    #     "id": "askemo:0000001",
    #     "name": "population",
    #     "physical_min": 0.0,
    #     "suggested_data_type": "int",
    #     "suggested_unit": "person",
    #     "synonyms": [
    #       {
    #         "type": "referenced_by_latex",
    #         "value": "N_i"
    #       }
    #     "type": "class",
    #     "xrefs": [
    #       {
    #         "id": "ido:0000509",
    #         "type": "skos:exactMatch"
    #       }
    #     ]
    #   }, ...]

    # Map from column name to json key in the output

    json_records = sheet_df.to_dict(orient="records")
    terms = {}
    for record in json_records:
        identifier = record["ASKEMOSW"]
        if not identifier:
            click.secho("Missing identifier!")
            continue

        out_record = {
            "id": identifier,
            "type": "class",
            # TODO: Add these fields to the google sheet
            "physical_min": None,
            "suggested_data_type": None,
            "suggested_unit": None,
            "dimension": None,  # This is a new field
        }

        # Description priority: description, grounded name, name
        # If the description is empty, use the grounded name if available
        # otherwise use the name column (which should always be populated)
        if record["description"]:
            out_record["description"] = record["description"]
        elif record["grounded name"]:
            out_record["description"] = record["grounded name"]
        else:
            out_record["description"] = record["name"]

        # Name priority: grounded name, name, suggested grounding, askemosw
        if record["grounded name"]:
            out_record["name"] = record["grounded name"]
        elif record["name"]:
            out_record["name"] = record["name"]
        elif record["suggested grounding"]:
            out_record["name"] = record["suggested grounding"]
        else:
            out_record["name"] = record["ASKEMOSW"]

        # If the symbol field has a value, put it in synonyms -> {type:
        # "referenced_by_latex", value: <symbol>}
        if record["symbol"]:
            # Get rid of the $ in the symbol and any accidental whitespace
            record["symbol"] = record["symbol"].replace("$", "").strip()

            # If the symbol string is only alphabetical, skip it
            if not record["symbol"].isalpha():
                out_record["synonyms"] = [
                    {"type": "referenced_by_latex", "value": record["symbol"]}
                ]

        # Grounding
        #   - Add 'suggested grounding' column as xrefs - skos:exactMatch
        #   - Add 'xrefs' column as xrefs - skos:exactMatch
        xrefs = []
        if record["suggested grounding"]:
            xrefs.append(
                {"type": "skos:exactMatch", "id": record["suggested grounding"]}
            )
        if record["xrefs"]:
            # Split on commas and remove whitespace
            xrefs.extend(
                [
                    {"type": "skos:exactMatch", "id": xref.strip()}
                    for xref in record["xrefs"].split(",")
                ]
            )

        if record["parent ASKEMOSW"]:
            out_record["parents"] = record["parent ASKEMOSW"].split(",")

        if xrefs:
            out_record["xrefs"] = xrefs

        if record["dimensions"]:
            out_record["dimensionality"] = record["dimensions"]

        term = Term(**out_record)
        terms[term.id] = term

    if path is not None:
        print(f"Writing to {path}")
        write(terms, Path(path))
    else:
        return terms


if __name__ == "__main__":
    # todo: propagate the dimensions to the google sheet
    df = read_google_sheet()
    export_to_json(df, HERE.joinpath("askemosw.json"))
