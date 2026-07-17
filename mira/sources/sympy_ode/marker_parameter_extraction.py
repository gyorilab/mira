"""
Marker parameter table extraction.

This script reads Marker HTML output, finds the parameter table using
string matching, extracts only the parameter rows, normalizes parameter
symbols, and writes the result to a CSV file.
"""

import argparse
import csv
import re
from dataclasses import asdict, dataclass
from html import unescape
from pathlib import Path
from typing import List


@dataclass
class ParameterRow:
    pmid: str
    table_id: str
    parameter: str
    definition: str
    value: str
    standard_deviation: str
    source: str
    parameter_type: str
    raw_parameter: str


def clean_text(text: str) -> str:
    """Basic text cleanup."""
    text = unescape(text)
    text = text.replace("\xa0", " ")
    text = text.replace("×", "x")
    text = text.replace("−", "-")
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = text.replace("\\times", "x")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def html_to_pipe_text(html_text: str) -> str:
    """
    Convert Marker HTML into a pipe-separated text representation.

    Marker output often preserves table-like structure with separators,
    but the text still needs cleanup before row extraction.
    """
    text = html_text

    # Preserve cell and row boundaries before removing tags.
    text = re.sub(r"</td\s*>|</th\s*>", " | ", text, flags=re.IGNORECASE)
    text = re.sub(r"</tr\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)

    # Remove remaining HTML tags.
    text = re.sub(r"<[^>]+>", " ", text)

    return clean_text(text)


def normalize_parameter(raw_parameter: str, definition: str) -> str:
    """
    Normalize parameter symbols from Marker output.

    This handles common Greek symbols and Marker symbol errors observed
    in the PMID 32046137 Marker extraction.
    """
    p = clean_text(raw_parameter)
    p = p.replace("\\", "")
    d = definition.lower()

    replacements = {
        "С": "c",          # Cyrillic-looking C sometimes appears instead of c
        "β": "beta",
        "σ": "sigma",
        "λ": "lambda",
        "α": "alpha",
        "δI": "delta_I",
        "δq": "delta_q",
        "γI": "gamma_I",
        "γA": "gamma_A",
        "γH": "gamma_H",
        "γн": "gamma_H",
        "delta I": "delta_I",
        "delta q": "delta_q",
        "gamma I": "gamma_I",
        "gamma A": "gamma_A",
        "gamma H": "gamma_H",
    }

    for old, new in replacements.items():
        p = p.replace(old, new)

    p = p.replace("{", "").replace("}", "")
    p = p.replace("$", "")
    p = re.sub(r"\s+", "", p)

    # Marker sometimes reads varrho/rho as Q in the symptoms row.
    if p in {"Q", "ρ", "𝜚"} and "symptoms" in d and "infected" in d:
        return "varrho"

    return p


def normalize_value(value: str) -> str:
    """Normalize numerical values and dashes."""
    value = clean_text(value)
    value = value.replace("{", "").replace("}", "")
    value = value.replace("_", "-") if value == "_" else value
    value = value.replace("10^{-", "10^-")
    value = value.replace("}", "")
    return value


def infer_parameter_type(parameter: str) -> str:
    """Separate model parameters from initial values."""
    if "(0)" in parameter:
        return "initial_value"
    return "model_parameter"


def extract_parameter_table_region(text: str) -> str:
    """
    Extract only the parameter table region from the full Marker output.

    This uses string matching to locate the table caption and stop before
    the next section.
    """
    lower = text.lower()

    start_candidates = [
        lower.find("table 1"),
        lower.find("parameter estimates"),
    ]
    start_candidates = [idx for idx in start_candidates if idx != -1]

    if not start_candidates:
        raise ValueError("Could not find the parameter table caption.")

    start = min(start_candidates)

    end_candidates = [
        lower.find("2.3. model-based", start),
        lower.find("model-based method", start),
        lower.find("given the model structure", start),
    ]
    end_candidates = [idx for idx in end_candidates if idx != -1]

    if end_candidates:
        end = min(end_candidates)
    else:
        end = min(len(text), start + 15000)

    return text[start:end]


def extract_marker_parameters(marker_html_path: Path, pmid: str, table_id: str) -> List[ParameterRow]:
    """
    Extract parameter rows from a Marker HTML file.

    The parser expects the parameter table to have five logical columns:
    Parameter, Definitions, Estimated Mean Value, Standard Deviation, Data Source.
    """
    raw_html = marker_html_path.read_text(errors="ignore")
    pipe_text = html_to_pipe_text(raw_html)
    table_region = extract_parameter_table_region(pipe_text)

    cells = [clean_text(cell) for cell in table_region.split("|")]
    cells = [cell for cell in cells if cell]

    valid_sources = {"mcmc", "who", "[18]", "[18,19]"}
    rows: List[ParameterRow] = []

    i = 0
    while i <= len(cells) - 5:
        raw_parameter = cells[i]
        definition = cells[i + 1]
        value = cells[i + 2]
        standard_deviation = cells[i + 3]
        source = cells[i + 4]

        source_key = source.lower().replace(" ", "")

        # This is the key string-matching rule:
        # A valid parameter row should end with a known source field.
        if source_key in valid_sources:
            parameter = normalize_parameter(raw_parameter, definition)

            # Skip accidental header rows.
            if parameter.lower() in {"parameter", "initialvalues", "definitions"}:
                i += 1
                continue

            rows.append(
                ParameterRow(
                    pmid=pmid,
                    table_id=table_id,
                    parameter=parameter,
                    definition=definition,
                    value=normalize_value(value),
                    standard_deviation=normalize_value(standard_deviation),
                    source=source,
                    parameter_type=infer_parameter_type(parameter),
                    raw_parameter=raw_parameter,
                )
            )

            i += 5
        else:
            i += 1

    return rows


def write_csv(rows: List[ParameterRow], output_path: Path) -> None:
    """Write extracted parameter rows to CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "pmid",
        "table_id",
        "parameter",
        "definition",
        "value",
        "standard_deviation",
        "source",
        "parameter_type",
        "raw_parameter",
    ]

    with output_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract parameter rows from Marker HTML output."
    )
    parser.add_argument("marker_html", type=Path, help="Path to Marker HTML file.")
    parser.add_argument("--pmid", required=True, help="PMID for the paper.")
    parser.add_argument("--table-id", default="Table 1", help="Table identifier.")
    parser.add_argument("--out", type=Path, required=True, help="Output CSV path.")

    args = parser.parse_args()

    rows = extract_marker_parameters(
        marker_html_path=args.marker_html,
        pmid=args.pmid,
        table_id=args.table_id,
    )

    write_csv(rows, args.out)

    print(f"Extracted {len(rows)} parameter rows")
    print(f"Saved to: {args.out}")

    for row in rows:
        print(
            f"{row.parameter} | {row.value} | "
            f"{row.standard_deviation} | {row.source}"
        )


if __name__ == "__main__":
    main()
