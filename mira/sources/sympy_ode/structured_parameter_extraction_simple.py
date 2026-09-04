"""Extract a simplified set of model-parameter fields from CSV tables."""

import argparse
import csv
import json
import os
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, Field


DEFAULT_PMIDS = [
    "32046137",
    "32099934",
    "32703315",
    "32706790",
    "32735581",
    "32834593",
]


class ParameterRecord(BaseModel):
    """One parameter extracted from a table."""

    symbol: str | None = Field(
        default=None,
        description="Mathematical symbol or variable name for the parameter.",
    )
    description: str | None = Field(
        default=None,
        description="Definition, meaning, or description of the parameter.",
    )
    value: str | None = Field(
        default=None,
        description="Parameter value exactly as written in the table.",
    )
    unit: str | None = Field(
        default=None,
        description="Unit exactly as written in the table.",
    )
    uncertainty: str | None = Field(
        default=None,
        description=(
            "Uncertainty information exactly as written, such as standard "
            "deviation, standard error, confidence interval, or credible interval."
        ),
    )


class PaperExtraction(BaseModel):
    """Structured parameter extraction for one paper."""

    pmid: str
    contains_parameter_information: bool
    parameters: list[ParameterRecord]


SYSTEM_PROMPT = """
You are extracting model parameters from CSV tables that were previously
extracted from a biomedical paper.

The input contains one or more CSV tables from the same paper.

Your task is to determine whether the tables contain model parameter
information. If they do, extract one record for each parameter.

Extract only these five fields:

1. symbol
2. description
3. value
4. unit
5. uncertainty

Field mapping:

- Parameter Symbol, Symbol, Variable, or mathematical notation -> symbol
- Parameter, Definition, Description, Meaning, Interpretation, or
  Epidemiological Meaning -> description
- Value, Estimated Mean, Estimated Mean Value, Best-fit Value,
  Baseline Value, Initial Value, or Default Value -> value
- Unit or Units -> unit
- Standard Deviation, Standard Error, Variance, Confidence Interval,
  Credible Interval, Range used as uncertainty, or another uncertainty
  measurement -> uncertainty

Extraction rules:

- Extract one record for each distinct parameter.
- Read all supplied CSV tables from the paper.
- Preserve mathematical symbols exactly as written.
- Preserve values and units exactly as written.
- Do not calculate, estimate, or invent missing values.
- Return null when a field is not present.
- Do not place a parameter symbol in the description field.
- Do not place explanatory text in the symbol field.
- If one table gives a symbol or description and another gives its value,
  combine them only when the same symbol clearly connects the records.
- Never merge two different parameter symbols.
- If a cell contains several newline-separated symbols, descriptions, or
  values, align them by position only when the correspondence is clear.
- If the correspondence is unclear, do not guess.
- Do not extract ordinary study statistics, participant characteristics,
  outcome measurements, or table values that are not model parameters.
- Do not return fields other than symbol, description, value, unit,
  and uncertainty inside each parameter record.

If none of the tables contain model parameter information, set
contains_parameter_information to false and return an empty parameter list.
""".strip()


def read_csv_table(csv_path: Path) -> dict:
    """Read one CSV table and retain its rows and headers."""

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        headers = reader.fieldnames or []
        rows = []

        for row_number, row in enumerate(reader, start=2):
            cleaned_row = {
                str(key): value
                for key, value in row.items()
                if key is not None
                and value is not None
                and str(value).strip() != ""
            }

            if cleaned_row:
                rows.append(
                    {
                        "csv_row_number": row_number,
                        "cells": cleaned_row,
                    }
                )

    return {
        "table_file": csv_path.name,
        "headers": headers,
        "rows": rows,
    }


def find_pmid_directory(input_root: Path, pmid: str) -> Path | None:
    """Find the directory containing the CSV files for a PMID."""

    direct_path = input_root / pmid

    if direct_path.is_dir():
        return direct_path

    matches = [
        path
        for path in input_root.rglob("*")
        if path.is_dir() and path.name == pmid
    ]

    if matches:
        return matches[0]

    return None


def load_paper_tables(input_root: Path, pmid: str) -> list[dict]:
    """Load all CSV tables belonging to a PMID."""

    pmid_directory = find_pmid_directory(input_root, pmid)

    if pmid_directory is None:
        return []

    csv_paths = sorted(pmid_directory.glob("*.csv"))

    return [read_csv_table(path) for path in csv_paths]


def extract_parameters(
    client: OpenAI,
    pmid: str,
    tables: list[dict],
    model: str,
) -> PaperExtraction:
    """Send all CSV tables for one paper to the model."""

    table_input = json.dumps(
        {
            "pmid": pmid,
            "tables": tables,
        },
        ensure_ascii=False,
        indent=2,
    )

    response = client.responses.parse(
        model=model,
        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": table_input,
            },
        ],
        text_format=PaperExtraction,
    )

    result = response.output_parsed

    if result is None:
        raise RuntimeError(f"No parsed structured output returned for {pmid}")

    result.pmid = pmid
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract symbol, description, value, unit, and uncertainty "
            "from CSV tables."
        )
    )

    parser.add_argument(
        "input_root",
        type=Path,
        help="Root folder containing one folder per PMID.",
    )
    parser.add_argument(
        "output_root",
        type=Path,
        help="Folder where JSON outputs will be saved.",
    )
    parser.add_argument(
        "--pmids",
        nargs="+",
        default=DEFAULT_PMIDS,
        help="PMIDs to process.",
    )
    parser.add_argument(
        "--model",
        default="gpt-4.1-mini",
        help="OpenAI model to use.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read the CSV files without calling the OpenAI API.",
    )

    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)

    client = None

    if not args.dry_run:
        if not os.getenv("OPENAI_API_KEY"):
            raise EnvironmentError(
                "OPENAI_API_KEY is not set in the current terminal."
            )

        client = OpenAI()

    for pmid in args.pmids:
        tables = load_paper_tables(args.input_root, pmid)

        if not tables:
            print(f"{pmid}: no CSV tables found")
            continue

        row_count = sum(len(table["rows"]) for table in tables)

        if args.dry_run:
            print(
                f"{pmid}: {len(tables)} tables, "
                f"{row_count} non-empty rows"
            )
            continue

        print(f"Processing PMID {pmid}...")

        result = extract_parameters(
            client=client,
            pmid=pmid,
            tables=tables,
            model=args.model,
        )

        output_path = args.output_root / f"{pmid}.json"

        output_path.write_text(
            json.dumps(
                result.model_dump(),
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        print(
            f"Saved {output_path} "
            f"({len(result.parameters)} records)"
        )


if __name__ == "__main__":
    main()
