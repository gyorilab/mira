import json
import math
import os
from typing import List

import pandas as pd

header_row = 1
row_count = 59
columns = list(range(10))
google_sheet_csv_export_url = os.environ["SPACE_ONTOLOGY_URL"]


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
    #         "value": "N"
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
    column_mapping = {
        "description": "description",
        "ASKEMOSW": "id",
        "name": "name",
        "suggested grounding": "xrefs",
        "grounded name": "name",
    }

    json_records = sheet_df.to_dict(orient="records")
    output_records = []
    for record in json_records:
        out_record = {}

        # If the description is empty, use the grounded name if available
        # otherwise use the name column (which should always be populated)
        if record["description"]:
            out_record["description"] = record["description"]
        elif record["grounded name"]:
            out_record["description"] = record["grounded name"]
        else:
            out_record["description"] = record["name"]

        # If the symbol field has a value, put it in synonyms -> {type:
        # "referenced_by_latex", value: <symbol>}
        if record["symbol"] and not (
            isinstance(record["symbol"], float) and math.isnan(record["symbol"])
        ):
            # Get rid of the $ in the symbol and any accidental whitespace
            record["symbol"] = record["symbol"].replace("$", "").strip()

            # If the symbol string is only alphabetical, skip it
            if not record["symbol"].isalpha():
                out_record["synonyms"] = [
                    {"type": "referenced_by_latex", "value": record["symbol"]}
                ]

        for column_name, json_key in column_mapping.items():
            if column_name == "suggested grounding":
                out_record[json_key] = [
                    {"id": record[column_name], "type": "skos:exactMatch"}
                ]
            else:
                out_record[json_key] = record[column_name]

        out_record["type"] = "class"

        # TODO: Add these fields to the google sheet
        out_record["physical_min"] = None
        out_record["suggested_data_type"] = None
        out_record["suggested_unit"] = None

        # Replace float nan with None
        for k, v in out_record.items():
            if isinstance(v, float) and math.isnan(v):
                out_record[k] = None
            elif k == "xrefs":
                for xr in v:
                    for k2, v2 in xr.items():
                        if isinstance(v2, float) and math.isnan(v2):
                            xr[k2] = None

        output_records.append(out_record)

    if path is not None:
        print(f"Writing to {path}")
        with open(path, "w") as f:
            json.dump(output_records, f, indent=2)
    else:
        return output_records


if __name__ == "__main__":
    df = read_google_sheet()
    export_to_json(df, "askemosw.json")
