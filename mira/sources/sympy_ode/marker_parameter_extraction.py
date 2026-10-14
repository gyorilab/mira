"""
Marker parameter table extraction utility.

This script extracts parameter tables from Marker HTML output.

It supports:
1. Single-file extraction
2. Batch-folder extraction

Main idea:
- Convert Marker HTML into pipe-separated text.
- Find table sections whose captions look parameter-related.
- Extract 5-column parameter rows:
  parameter | definition | value | standard_deviation | source
- Also support shorter 4-column and 3-column parameter tables.
"""

import argparse
import csv
import re
from dataclasses import asdict, dataclass
from html import unescape
from pathlib import Path
from typing import Iterable, List, Optional, Sequence
from bs4 import BeautifulSoup

try:
    from .parameter_table_classifier import ParameterTableClassifier
except ImportError:
    # Supports running this file directly from Terminal.
    from parameter_table_classifier import ParameterTableClassifier



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


def clean_cell(text: str) -> str:
    text = unescape(str(text))
    text = text.replace("\xa0", " ")
    text = text.replace("×", "x")
    text = text.replace("−", "-")
    text = text.replace("–", "-")
    text = text.replace("—", "-")
    text = text.replace("\\times", "x")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def html_to_text(html_text: str) -> str:
    text = html_text

    text = re.sub(r"</td\s*>|</th\s*>", " | ", text, flags=re.I)
    text = re.sub(r"</tr\s*>", "\n", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.I)
    text = re.sub(r"</div\s*>", "\n", text, flags=re.I)

    text = re.sub(r"<[^>]+>", " ", text)

    lines = []
    for line in unescape(text).splitlines():
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)

    return "\n".join(lines)


def get_pmid_from_filename(path: Path) -> str:
    match = re.search(r"(\d{7,8})", path.name)
    return match.group(1) if match else path.stem


def normalize_parameter(raw_parameter: str, definition: str = "") -> str:
    p = clean_cell(raw_parameter)
    d = definition.lower()

    p = p.replace("\\", "")

    replacements = {
        "С": "c",
        "β": "beta",
        "𝛽": "beta",
        "σ": "sigma",
        "𝜎": "sigma",
        "λ": "lambda",
        "𝜆": "lambda",
        "α": "alpha",
        "𝛼": "alpha",
        "δ": "delta",
        "𝛿": "delta",
        "γ": "gamma",
        "𝛾": "gamma",
        "ρ": "rho",
        "ϱ": "varrho",
        "𝜚": "varrho",
        "θ": "theta",
        "𝜃": "theta",
        "μ": "mu",
        "𝜇": "mu",
    }

    for old, new in replacements.items():
        p = p.replace(old, new)

    p = p.replace("{", "").replace("}", "")
    p = p.replace("$", "")
    p = re.sub(r"\s+", "", p)

    p = re.sub(r"delta_?I$", "delta_I", p, flags=re.I)
    p = re.sub(r"delta_?q$", "delta_q", p, flags=re.I)
    p = re.sub(r"gamma_?I$", "gamma_I", p, flags=re.I)
    p = re.sub(r"gamma_?A$", "gamma_A", p, flags=re.I)
    p = re.sub(r"gamma_?H$", "gamma_H", p, flags=re.I)

    p = p.replace("gammaI", "gamma_I")
    p = p.replace("gammaA", "gamma_A")
    p = p.replace("gammaH", "gamma_H")
    p = p.replace("deltaI", "delta_I")
    p = p.replace("deltaq", "delta_q")

    if p in {"Q", "q", "rho"} and "symptoms" in d and "infected" in d:
        return "varrho"

    return p



def clean_parameter_definition(
    raw_definition: str,
    parameter_symbol: str,
) -> str:
    """Remove a parameter symbol from its descriptive text."""

    definition = clean_cell(raw_definition)
    symbol = clean_cell(parameter_symbol)

    if not definition:
        return ""

    if not symbol:
        return definition

    escaped_symbol = re.escape(symbol)

    # Symbol at the beginning:
    # beta Transmission rate
    # beta: Transmission rate
    # beta - Transmission rate
    definition = re.sub(
        rf"^\s*{escaped_symbol}\s*[:;,=\-–—]?\s*",
        "",
        definition,
        flags=re.IGNORECASE,
    )

    # Symbol inside parentheses:
    # Transmission rate (beta)
    definition = re.sub(
        rf"\(\s*{escaped_symbol}\s*\)",
        "",
        definition,
        flags=re.IGNORECASE,
    )

    # Symbol at the end:
    # Transmission rate, beta
    definition = re.sub(
        rf"[,;:\s]+{escaped_symbol}\s*$",
        "",
        definition,
        flags=re.IGNORECASE,
    )

    definition = re.sub(r"\s+", " ", definition)

    return definition.strip(" ,;:-–—")


def normalize_value(text: str) -> str:
    """Keep only the first numerical estimate in a value cell."""

    cleaned = clean_cell(text)

    if not cleaned:
        return ""

    match = re.search(
        r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?",
        cleaned,
    )

    if match:
        return match.group(0)

    return cleaned

def infer_parameter_type(parameter: str) -> str:
    if "(0)" in parameter:
        return "initial_value"
    return "model_parameter"


def looks_like_parameter_caption(text: str) -> bool:
    lower = text.lower()

    phrases = [
        "parameter estimates",
        "parameter estimation",
        "parameter inference",
        "parameter values",
        "estimated parameters",
        "model parameters",
        "input parameters",
        "parameters used",
        "parameter description",
        "parameter definitions",
    ]

    return any(phrase in lower for phrase in phrases)


def split_into_table_sections(text: str) -> List[str]:
    matches = list(re.finditer(r"\bTable\s+\d+\.?", text, flags=re.I))

    if not matches:
        return [text]

    sections = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections.append(text[start:end])

    return sections


def extract_table_id(section: str, fallback: str = "auto") -> str:
    match = re.search(r"\bTable\s+(\d+)", section, flags=re.I)
    return f"Table {match.group(1)}" if match else fallback


def split_cells(section: str) -> List[str]:
    cells = [clean_cell(cell) for cell in section.split("|")]
    return [cell for cell in cells if cell]


def looks_like_source(text: str) -> bool:
    text = clean_cell(text)
    s = text.lower().replace(" ", "")

    if not s:
        return False

    known_sources = {
        "mcmc",
        "who",
        "cdc",
        "nih",
        "literature",
        "estimated",
        "assumed",
        "fitted",
        "calculated",
        "reported",
        "data",
        "thisstudy",
        "modelcalibration",
    }

    if s in known_sources:
        return True

    if re.search(r"\[\d+", s):
        return True

    keywords = [
        "assumed",
        "estimate",
        "estimated",
        "fitted",
        "calibrated",
        "calculated",
        "literature",
        "reported",
        "derived",
        "reference",
        "data",
        "study",
        "baseline",
        "supplement",
    ]

    return any(keyword in s for keyword in keywords)


def looks_like_value(text: str) -> bool:
    text = clean_cell(text).lower()

    if not text:
        return False

    if text in {"-", "_", "na", "n/a"}:
        return True

    if re.search(r"\d", text):
        return True

    return False


def looks_like_parameter_name(text: str) -> bool:
    text = clean_cell(text)
    lower = text.lower()

    if not text or len(text) > 100:
        return False

    banned = {
        "parameter",
        "parameters",
        "definition",
        "definitions",
        "description",
        "estimated mean value",
        "standard deviation",
        "data source",
        "source",
        "value",
        "values",
        "initial values",
        "peak time",
        "value of i at peak time",
        "figure",
        "note",
    }

    if lower in banned:
        return False

    if lower.startswith("table "):
        return False

    # Marker sometimes outputs contact-rate c as a Cyrillic-looking C.
    if text in {"c", "C", "С"}:
        return True

    return bool(re.search(r"[A-Za-zСαβγδλσρϱθ_()]", text))


def parse_source_based_rows(
    cells: List[str],
    pmid: str,
    table_id: str,
) -> List[ParameterRow]:
    """
    Parse rows using the pattern:
    parameter | definition | value | standard_deviation | source

    This is useful for Marker outputs where the table is flattened but
    source cells like MCMC, WHO, [18], etc. are preserved.
    """
    rows: List[ParameterRow] = []
    seen = set()

    i = 0
    while i <= len(cells) - 5:
        raw_parameter = cells[i]
        definition = cells[i + 1]
        value = cells[i + 2]
        standard_deviation = cells[i + 3]
        source = cells[i + 4]

        if (
            looks_like_parameter_name(raw_parameter)
            and looks_like_value(value)
            and looks_like_source(source)
        ):
            parameter = normalize_parameter(raw_parameter, definition)

            key = (parameter, normalize_value(value), source)
            if key not in seen:
                seen.add(key)
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


def parse_short_rows(
    cells: List[str],
    pmid: str,
    table_id: str,
) -> List[ParameterRow]:
    """
    Fallback for parameter tables with fewer columns:
    parameter | definition | value
    parameter | definition | value | source
    """
    rows: List[ParameterRow] = []
    seen = set()

    for width in [4, 3]:
        i = 0
        while i <= len(cells) - width:
            raw_parameter = cells[i]
            definition = cells[i + 1]
            value = cells[i + 2]
            source = cells[i + 3] if width == 4 else ""

            if not looks_like_parameter_name(raw_parameter):
                i += 1
                continue

            if not looks_like_value(value):
                i += 1
                continue

            if width == 4 and source and not looks_like_source(source):
                i += 1
                continue

            parameter = normalize_parameter(raw_parameter, definition)
            key = (parameter, normalize_value(value), source)

            if key not in seen:
                seen.add(key)
                rows.append(
                    ParameterRow(
                        pmid=pmid,
                        table_id=table_id,
                        parameter=parameter,
                        definition=definition,
                        value=normalize_value(value),
                        standard_deviation="",
                        source=source,
                        parameter_type=infer_parameter_type(parameter),
                        raw_parameter=raw_parameter,
                    )
                )

            i += width

    return rows



def extract_html_tables(html_text: str) -> List[dict]:
    """Extract structured rows directly from HTML table elements.

    Each returned dictionary contains:

    - table_id
    - caption
    - headers
    - rows

    The original HTML row and column structure is preserved instead of
    converting the table into one flattened text section.
    """

    soup = BeautifulSoup(html_text, "html.parser")
    extracted_tables: List[dict] = []

    for table_number, table in enumerate(
        soup.find_all("table"),
        start=1,
    ):
        matrix: List[List[str]] = []

        for tr in table.find_all("tr"):
            cells = tr.find_all(["th", "td"])

            row = [
                clean_cell(
                    cell.get_text(" ", strip=True)
                )
                for cell in cells
            ]

            row = [cell for cell in row if cell]

            if row:
                matrix.append(row)

        if not matrix:
            continue

        caption_tag = table.find("caption")

        if caption_tag is not None:
            caption = clean_cell(
                caption_tag.get_text(" ", strip=True)
            )
        else:
            caption = ""

            # Marker HTML does not always use a <caption> element.
            # Look immediately before the table for a likely caption.
            previous_element = table.find_previous(
                ["p", "h1", "h2", "h3", "h4", "div"]
            )

            if previous_element is not None:
                candidate_caption = clean_cell(
                    previous_element.get_text(" ", strip=True)
                )

                if len(candidate_caption) <= 1000:
                    caption = candidate_caption

        table_id = f"Table {table_number}"

        caption_match = re.search(
            r"\btable\s+([a-z0-9]+)",
            caption,
            re.IGNORECASE,
        )

        if caption_match:
            table_id = f"Table {caption_match.group(1)}"

        first_html_row = table.find("tr")
        first_row_has_header_cells = bool(
            first_html_row
            and first_html_row.find_all("th")
        )

        header_terms = {
            "parameter",
            "parameters",
            "symbol",
            "description",
            "definition",
            "meaning",
            "value",
            "values",
            "estimate",
            "estimated value",
            "unit",
            "units",
            "source",
            "standard deviation",
            "range",
        }

        first_row_text = " ".join(
            cell.lower()
            for cell in matrix[0]
        )

        first_row_looks_like_header = (
            first_row_has_header_cells
            or any(
                term in first_row_text
                for term in header_terms
            )
        )

        if first_row_looks_like_header:
            headers = matrix[0]
            data_rows = matrix[1:]
        else:
            headers = []
            data_rows = matrix

        extracted_tables.append(
            {
                "table_id": table_id,
                "caption": caption,
                "headers": headers,
                "rows": data_rows,
            }
        )

    return extracted_tables


def parse_two_column_rows(
    table_rows: Sequence[Sequence[str]],
    pmid: str,
    table_id: str,
) -> List[ParameterRow]:
    """Parse parameter tables with a label column and a value column.

    Example:

        Effective contact rate (beta) | 1.30 [1.21-1.39] day-1
    """

    rows: List[ParameterRow] = []
    seen = set()

    for table_row in table_rows:
        if len(table_row) < 2:
            continue

        raw_parameter = clean_cell(table_row[0])
        raw_value = clean_cell(
            " ".join(table_row[1:])
        )

        if not raw_parameter or not raw_value:
            continue

        lowered_parameter = raw_parameter.lower()

        if lowered_parameter in {
            "parameter",
            "parameters",
            "parameter name",
            "description",
            "definition",
            "symbol",
        }:
            continue

        if not looks_like_value(raw_value):
            continue

        parameter = normalize_parameter(
            raw_parameter,
            raw_parameter,
        )

        if not looks_like_parameter_name(parameter):
            continue

        definition = clean_parameter_definition(
            raw_parameter,
            parameter,
        )

        value = normalize_value(raw_value)

        key = (
            parameter,
            value,
        )

        if key in seen:
            continue

        seen.add(key)

        rows.append(
            ParameterRow(
                pmid=pmid,
                table_id=table_id,
                parameter=parameter,
                definition=definition,
                value=value,
                standard_deviation="",
                source="",
                parameter_type=infer_parameter_type(parameter),
                raw_parameter=raw_parameter,
            )
        )

    return rows


def flatten_table_rows(
    table_rows: Sequence[Sequence[str]],
) -> List[str]:
    """Flatten a real HTML matrix for the existing fallback parsers."""

    return [
        clean_cell(cell)
        for row in table_rows
        for cell in row
        if clean_cell(cell)
    ]


def extract_marker_parameters(
    marker_html_path: Path,
    pmid: Optional[str] = None,
    table_id: str = "auto",
) -> List[ParameterRow]:
    """Extract parameter rows from structured Marker HTML tables."""

    if pmid is None:
        pmid = get_pmid_from_filename(marker_html_path)

    html_text = marker_html_path.read_text(errors="ignore")

    all_rows: List[ParameterRow] = []
    seen = set()

    classifier = ParameterTableClassifier(threshold=0.43)

    html_tables = extract_html_tables(html_text)

    if not html_tables:
        print(
            f"{pmid}: no structured HTML tables were found"
        )
        return all_rows

    for html_table in html_tables:
        current_table_id = html_table["table_id"]

        if table_id != "auto":
            current_table_id = table_id

        caption = html_table["caption"]
        headers = html_table["headers"]
        table_rows = html_table["rows"]

        if not table_rows:
            continue

        classification = classifier.predict(
            caption=caption,
            headers=headers,
            rows=table_rows,
        )

        print(
            f"{pmid} | table={current_table_id} | "
            f"html_rows={len(table_rows)} | "
            f"columns={max(len(row) for row in table_rows)} | "
            f"parameter={classification.is_parameter_table} | "
            f"score={classification.score:.4f} | "
            f"caption={classification.caption_similarity:.4f} | "
            f"header={classification.header_similarity:.4f} | "
            f"keywords={classification.keyword_score:.4f} | "
            f"numeric={classification.numeric_density:.4f} | "
            f"symbols={classification.symbol_density:.4f} | "
            f"negative={classification.negative_keyword_score:.4f}"
        )

        if not classification.is_parameter_table:
            continue

        # First try the new parser for tables with one label column
        # and one value column.
        rows = parse_two_column_rows(
            table_rows,
            pmid=pmid,
            table_id=current_table_id,
        )

        # Existing parsers remain available for 3-, 4-, and 5-column
        # parameter tables.
        if not rows:
            flattened_cells = flatten_table_rows(table_rows)

            rows = parse_source_based_rows(
                flattened_cells,
                pmid=pmid,
                table_id=current_table_id,
            )

            if not rows:
                rows = parse_short_rows(
                    flattened_cells,
                    pmid=pmid,
                    table_id=current_table_id,
                )

        if not rows:
            print(
                f"  Accepted as a parameter table, "
                f"but no parameter rows were parsed."
            )

            print("  First HTML rows:")

            for raw_row in table_rows[:5]:
                print(f"    {raw_row!r}")

            continue

        print(f"  Parsed parameter rows: {len(rows)}")

        for row in rows:
            key = (
                row.pmid,
                row.table_id,
                row.parameter,
                row.value,
            )

            if key not in seen:
                seen.add(key)
                all_rows.append(row)

    return all_rows


def write_csv(rows: Iterable[ParameterRow], output_path: Path) -> None:
    rows = list(rows)
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


def run_single_file(args) -> None:
    rows = extract_marker_parameters(
        marker_html_path=args.marker_html,
        pmid=args.pmid,
        table_id=args.table_id,
    )

    write_csv(rows, args.out)

    print(f"Extracted {len(rows)} parameter rows")
    print(f"Saved to: {args.out}")

    for row in rows:
        print(f"{row.parameter} | {row.value} | {row.standard_deviation} | {row.source}")


def run_batch(args) -> None:
    input_dir = args.input_dir
    output_dir = args.output_dir
    summary_path = args.summary

    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    html_files = sorted(input_dir.glob("*.html"))
    summary_rows = []

    for html_file in html_files:
        pmid = get_pmid_from_filename(html_file)
        out_csv = output_dir / f"{pmid}_marker_parameters.csv"

        try:
            rows = extract_marker_parameters(html_file, pmid=pmid, table_id="auto")
            write_csv(rows, out_csv)

            status = "extracted" if rows else "zero_rows_needs_review"
            print(f"{pmid}: {len(rows)} rows ({status})")

            summary_rows.append({
                "pmid": pmid,
                "rows_extracted": len(rows),
                "status": status,
                "input_file": str(html_file),
                "output_file": str(out_csv),
            })

        except Exception as error:
            print(f"{pmid}: failed ({error})")
            summary_rows.append({
                "pmid": pmid,
                "rows_extracted": 0,
                "status": f"failed: {error}",
                "input_file": str(html_file),
                "output_file": str(out_csv),
            })

    with summary_path.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["pmid", "rows_extracted", "status", "input_file", "output_file"],
        )
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nBatch summary saved to: {summary_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract parameter rows from Marker HTML output."
    )

    parser.add_argument("marker_html", type=Path, nargs="?", help="Path to one Marker HTML file.")
    parser.add_argument("--pmid", help="PMID for single-file mode.")
    parser.add_argument("--table-id", default="auto", help="Table identifier.")
    parser.add_argument("--out", type=Path, help="Output CSV path for single-file mode.")

    parser.add_argument("--input-dir", type=Path, help="Folder containing Marker HTML files.")
    parser.add_argument("--output-dir", type=Path, help="Folder for batch CSV outputs.")
    parser.add_argument("--summary", type=Path, help="Path to batch summary CSV.")

    args = parser.parse_args()

    if args.input_dir:
        if not args.output_dir or not args.summary:
            raise ValueError("Batch mode requires --output-dir and --summary.")
        run_batch(args)
    else:
        if not args.marker_html or not args.out:
            raise ValueError("Single-file mode requires marker_html and --out.")
        run_single_file(args)


if __name__ == "__main__":
    main()
