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
            "Parameter symbol from the supplied table, converted from "
            "LaTeX notation to plain text. Example: \\beta_c -> beta_c. "
            "Use '-' if no symbol is available."
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
            "Parameter value converted to plain-text notation. Preserve "
            "fractions, expressions, scientific notation, and explicit "
            "textual values such as Estimated, Fitted, Assumed, or Fixed. "
            "Use '-' only when no value is supplied."
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
You are extracting parameters from an EPIDEMIOLOGICAL ORDINARY
DIFFERENTIAL EQUATION (ODE) MODEL described in a scientific paper.

You are given multiple classifier-selected tables from the SAME paper.
The tables may contain complementary information about epidemiological
ODE model parameters.

The goal is to recover the BASELINE, DEFAULT, NOMINAL, INITIAL,
ASSUMED, ESTIMATED, or main parameter specification used to define or
initialize the epidemiological ODE model.

Different tables may contain complementary information.

For example:
- one table may contain parameter symbols and definitions;
- another table may contain baseline/default parameter values;
- another table may contain ranges, units, or uncertainty.

Use all supplied tables together.

PARAMETER EXTRACTION RULES:

1. Extract quantities that function as parameters or initial conditions
   of the epidemiological ODE model.

2. Prefer tables explicitly describing:
   - baseline values
   - default values
   - parameter values
   - nominal values
   - initial parameter values
   - assumed values
   - estimated parameters
   - model parameters
   - values used to initialize or simulate the ODE model

3. If one table defines parameter symbols and names and another table
   provides their values, combine the information using the same
   parameter symbol.

4. Match corresponding parameters primarily using the supplied
   parameter symbol.

5. CONVERT LATEX NOTATION TO PLAIN TEXT in the structured output.

   Examples:
   - \\beta       -> beta
   - \\beta_c     -> beta_c
   - \\sigma      -> sigma
   - \\rho_E      -> rho_E
   - \\frac{1}{7} -> 1/7
   - 10^{-5}        -> 10^-5

   Do not return LaTeX commands, backslashes, dollar signs, or
   unnecessary LaTeX braces in parameter_symbol, parameter_value,
   parameter_unit, uncertainty, or parameter_name.

   Preserve the scientific meaning of the original notation while
   converting only its representation to readable plain text.

6. parameter_name must contain only the descriptive name, definition,
   meaning, or interpretation of the parameter.

7. NEVER copy the parameter symbol itself into parameter_name.
   If no descriptive name or definition is supplied, return "-".

8. IMPORTANT: textual parameter specifications are VALID VALUES.

   If the source table explicitly gives a parameter value as:
   - Estimated
   - Fitted
   - Assumed
   - Calculated
   - Calibrated
   - Fixed
   - Derived
   or another explicit textual specification,

   preserve that exact textual specification in parameter_value.

   Do NOT convert "Estimated", "Fitted", "Assumed", or similar source
   values to "-" merely because they are not numerical.

9. A parameter is considered to have a value whenever the source
   explicitly provides either a numerical/mathematical value OR an
   explicit textual value such as "Estimated" or "Fitted".

10. Extract only ONE baseline/default parameter record per symbol when
    a baseline/default specification is available.

11. Do not replace a baseline/default specification with alternative
    fitted estimates from later result tables.

12. Ignore values that are clearly:
    - alternative fitted estimates when a baseline specification exists
    - repeated fitted datasets
    - scenario-specific estimates
    - country-specific result estimates
    - sensitivity-analysis results
    - PRCC/ePRCC coefficients
    - correlation coefficients
    - optimization outputs
    - simulation outcome values

13. If a parameter table's baseline value itself is explicitly written
    as "Estimated" or "Fitted", KEEP that word as parameter_value.
    Do not search later result tables for a numerical replacement unless
    the supplied tables clearly identify that number as the baseline value.

14. If a value contains an attached unit such as "0.5/day", separate
    the value and unit when this can be done directly without guessing.

15. A Range column, confidence interval, credible interval, bounds,
    standard deviation, or similar information should be returned as
    uncertainty.

16. Do not invent, calculate, average, infer, or guess missing
    parameter information.

17. definition_table_id must be the TABLE_ID of the supplied table that
    actually provides the descriptive parameter definition/name.

18. value_table_id must be the TABLE_ID of the supplied table that
    actually provides the chosen parameter value or uncertainty.

19. Never infer table provenance from the apparent content or expected
    numbering. Copy the TABLE_ID exactly from the supplied table block.

20. OMIT a parameter only when BOTH parameter_value AND uncertainty
    are genuinely unavailable ("-").

21. Treat tables whose captions describe "results of parameter
    estimation", "parameter estimates for selected countries",
    "fitted parameters for different datasets", "best fits", or similar
    result tables as CONTEXT-SPECIFIC RESULT TABLES, not as the
    baseline/default parameter set.

22. Do NOT create one structured parameter record per country, dataset,
    fit, scenario, group, or experimental condition for the same
    parameter symbol.

23. A table containing several numerical estimates for the same
    parameter across countries or fitting contexts must NOT be used as
    value_table_id for the baseline/default record.

24. If a definition table supplies a symbol and its meaning but no valid
    baseline/default value exists in the supplied tables, OMIT that
    parameter. Do not substitute country-specific fitted results.

25. The word "Estimated" or "Fitted" is still a valid textual
    parameter_value ONLY when that exact word appears in a baseline,
    default, assumed, nominal, or main parameter table as the parameter's
    stated value. This rule does NOT make numerical estimation-result
    tables eligible as baseline sources.

26. Return only information supported by the supplied tables.
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
