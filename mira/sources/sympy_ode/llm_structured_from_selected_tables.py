from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field


# ============================================================
# Structured output schema
# ============================================================

class ParameterRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter_symbol: str = Field(
        description=(
            "Mathematical parameter symbol exactly as represented "
            "in the supplied Marker table. Use '-' if unavailable."
        )
    )

    parameter_name: str = Field(
        description=(
            "Descriptive parameter name, definition, meaning, or "
            "interpretation. Use '-' if unavailable."
        )
    )

    parameter_value: str = Field(
        description=(
            "Parameter value. Preserve fractions, mathematical "
            "expressions, and scientific notation. Use '-' if unavailable."
        )
    )

    parameter_unit: str = Field(
        description=(
            "Unit associated with the parameter value. "
            "Use '-' if unavailable."
        )
    )

    uncertainty: str = Field(
        description=(
            "Range, confidence interval, standard deviation, bounds, "
            "or other uncertainty supplied for the parameter. "
            "Use '-' if unavailable."
        )
    )

    definition_table_id: str = Field(
        description=(
            "Table containing the parameter definition/name. "
            "Use '-' if no definition table supplied the name."
        )
    )

    value_table_id: str = Field(
        description=(
            "Table containing the parameter value or uncertainty. "
            "Use '-' if unavailable."
        )
    )


class ParameterExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameters: list[ParameterRecord]


# ============================================================
# System prompt
# ============================================================

SYSTEM_PROMPT = """
You are extracting structured mathematical model parameters from
multiple tables selected from the SAME scientific paper.

The goal is to recover the BASELINE, DEFAULT, NOMINAL, INITIAL,
ASSUMED, or main model parameter values used to define or initialize
the mathematical model.

Different supplied tables may contain complementary information.

For example:
- one table may contain parameter symbols and definitions;
- another table may contain baseline/default values;
- another table may contain ranges, units, or uncertainty.

Use all supplied tables together, but extract only the baseline/default
parameter set.

BASELINE PARAMETER RULES:

1. Prefer tables explicitly describing:
   - baseline values
   - default values
   - parameter values
   - nominal values
   - initial parameter values
   - assumed values
   - model parameters
   - values used in simulations

2. Ignore tables whose values are:
   - alternative fitted estimates
   - best-fit results
   - repeated fitted datasets
   - scenario-specific estimates
   - country-specific estimates
   - sensitivity-analysis results
   - PRCC/ePRCC coefficients
   - correlation coefficients
   - optimization outputs
   - multiple competing fits
   - simulation outcome values

3. If one table defines parameter symbols and names and another table
   provides the baseline/default value, combine them using the same
   parameter symbol.

4. Match parameters primarily using the supplied parameter symbol.

5. Preserve parameter symbols exactly as supplied by Marker.
   Do NOT normalize, rewrite, translate, correct, or redesign them.

6. parameter_name must contain only the descriptive name, definition,
   meaning, or interpretation of the parameter.

7. NEVER copy the mathematical symbol itself into parameter_name.
   If no descriptive parameter name is supplied, return "-".

8. Extract only ONE baseline/default record per parameter symbol unless
   the source explicitly defines multiple baseline values as distinct
   model parameters.

9. Do not arbitrarily choose among multiple fitted estimates. If only
   fitted/alternative estimates are available and no baseline/default
   value is supplied, do not use those fitted estimates as the baseline.

10. If a baseline value contains an attached unit such as "0.5/day",
    separate the value into parameter_value and the associated unit into
    parameter_unit when this can be done directly from the source text.

11. A Range column, bounds, confidence interval, standard deviation, or
    other uncertainty associated with the baseline value should be
    returned as uncertainty.

12. Preserve fractions, mathematical expressions, scientific notation,
    ranges, and numerical values exactly when possible.

13. Do not invent, calculate, infer, average, or guess missing values.

14. definition_table_id must identify the table that supplied the
    descriptive parameter definition/name.

15. value_table_id must identify the table that supplied the chosen
    baseline/default value or uncertainty.

16. If definition and baseline value come from the same table, both
    provenance fields may contain the same table ID.

17. OMIT a parameter completely when BOTH parameter_value AND uncertainty
    are unavailable ("-").

18. Return only information supported by the supplied tables.
"""


# ============================================================
# Helpers
# ============================================================

def clean(value) -> str:
    if value is None:
        return "-"
    value = str(value).strip()
    return value if value else "-"


def identity(value: str) -> str:
    """Loose comparison used only to prevent symbol -> name duplication."""
    value = clean(value).casefold()

    for char in (
        "\\",
        "{",
        "}",
        "$",
        " ",
        "_",
        "^",
    ):
        value = value.replace(char, "")

    return value


def read_selected_json(path: Path) -> dict:
    return json.loads(
        path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    )


def make_prompt(data: dict) -> str:
    pmid = clean(data.get("pmid"))
    tables = data.get("tables", [])

    chunks = [
        f"PMID: {pmid}",
        "",
        (
            "The following classifier-selected tables all come from "
            "the same paper. Use them together."
        ),
    ]

    for table in tables:
        table_id = clean(table.get("table_id"))
        caption = clean(table.get("caption"))
        headers = table.get("headers", [])
        rows = table.get("rows", [])

        chunks.append(
            "\n".join(
                [
                    "",
                    "=" * 70,
                    f"TABLE_ID: {table_id}",
                    f"CAPTION: {caption}",
                    "HEADERS:",
                    " | ".join(str(x) for x in headers),
                    "ROWS:",
                ]
            )
        )

        for index, row in enumerate(rows, start=1):
            chunks.append(
                f"{index}: "
                + " | ".join(str(x) for x in row)
            )

        chunks.append(f"END TABLE {table_id}")

    return "\n".join(chunks)


def call_llm(
    client: OpenAI,
    data: dict,
    model: str,
) -> ParameterExtraction:

    response = client.responses.create(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=make_prompt(data),
        text={
            "format": {
                "type": "json_schema",
                "name": "parameter_extraction",
                "schema": ParameterExtraction.model_json_schema(),
                "strict": True,
            }
        },
    )

    return ParameterExtraction.model_validate_json(
        response.output_text
    )


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--selected-dir",
        required=True,
        type=Path,
        help=(
            "Directory containing *_selected_tables.json files "
            "produced by the deterministic classifier/extractor."
        ),
    )

    parser.add_argument(
        "--output-dir",
        required=True,
        type=Path,
    )

    parser.add_argument(
        "--num-pmids",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--model",
        default="gpt-5-mini",
    )

    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not configured."
        )

    selected_dir = args.selected_dir.expanduser()
    output_dir = args.output_dir.expanduser()

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    paths = sorted(
        selected_dir.glob("*_selected_tables.json")
    )

    selected = []

    for path in paths:
        try:
            data = read_selected_json(path)
        except Exception:
            continue

        tables = data.get("tables", [])

        if not tables:
            continue

        pmid = clean(data.get("pmid"))

        if pmid == "-":
            pmid = path.name.replace(
                "_selected_tables.json",
                "",
            )

        selected.append(
            (pmid, path, data)
        )

        if len(selected) == args.num_pmids:
            break

    print(
        f"Selected {len(selected)} PMIDs "
        f"from classifier-selected table JSON files.",
        flush=True,
    )

    client = OpenAI()

    combined = []
    log_rows = []

    for index, (pmid, path, data) in enumerate(
        selected,
        start=1,
    ):
        tables = data.get("tables", [])

        table_ids = [
            clean(table.get("table_id"))
            for table in tables
        ]

        print(
            f"[{index}/{len(selected)}] "
            f"{pmid}: {len(tables)} useful tables "
            f"({', '.join(table_ids)})",
            flush=True,
        )

        try:
            result = call_llm(
                client,
                data,
                args.model,
            )

            kept = []

            for parameter in result.parameters:
                value = clean(
                    parameter.parameter_value
                )
                uncertainty = clean(
                    parameter.uncertainty
                )

                # Required rule:
                # no value + no uncertainty = no record.
                if (
                    value == "-"
                    and uncertainty == "-"
                ):
                    continue

                symbol = clean(
                    parameter.parameter_symbol
                )

                name = clean(
                    parameter.parameter_name
                )

                # Never allow the symbol itself to become
                # the descriptive parameter name.
                if (
                    symbol != "-"
                    and name != "-"
                    and identity(symbol)
                    == identity(name)
                ):
                    name = "-"

                record = {
                    "pmid": pmid,
                    "definition_table_id": clean(
                        parameter.definition_table_id
                    ),
                    "value_table_id": clean(
                        parameter.value_table_id
                    ),
                    "parameter_symbol": symbol,
                    "parameter_name": name,
                    "parameter_value": value,
                    "parameter_unit": clean(
                        parameter.parameter_unit
                    ),
                    "uncertainty": uncertainty,
                }

                kept.append(record)
                combined.append(record)

            print(
                f"    -> {len(kept)} structured records",
                flush=True,
            )

            log_rows.append({
                "pmid": pmid,
                "tables_supplied": "; ".join(table_ids),
                "number_of_tables": len(tables),
                "structured_rows": len(kept),
                "status": "success",
                "error": "-",
            })

        except Exception as error:
            print(
                f"    ERROR: {error}",
                flush=True,
            )

            log_rows.append({
                "pmid": pmid,
                "tables_supplied": "; ".join(table_ids),
                "number_of_tables": len(tables),
                "structured_rows": 0,
                "status": "error",
                "error": str(error),
            })

    output_csv = (
        output_dir
        / f"structured_parameters_{len(selected)}_pmids.csv"
    )

    fields = [
        "pmid",
        "definition_table_id",
        "value_table_id",
        "parameter_symbol",
        "parameter_name",
        "parameter_value",
        "parameter_unit",
        "uncertainty",
    ]

    with output_csv.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )
        writer.writeheader()
        writer.writerows(combined)

    log_path = (
        output_dir
        / "structured_output_log.csv"
    )

    with log_path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "pmid",
                "tables_supplied",
                "number_of_tables",
                "structured_rows",
                "status",
                "error",
            ],
        )
        writer.writeheader()
        writer.writerows(log_rows)

    selected_path = (
        output_dir
        / "selected_pmids.txt"
    )

    selected_path.write_text(
        "\n".join(
            f"{i}. {pmid}"
            for i, (pmid, _, _) in enumerate(
                selected,
                start=1,
            )
        )
        + "\n",
        encoding="utf-8",
    )

    print()
    print("PMIDs processed:", len(selected))
    print("Structured records:", len(combined))
    print("Output:", output_csv)


if __name__ == "__main__":
    main()
