"""Deterministic parameter-table extraction from Marker HTML output.

Parses tables with BeautifulSoup, scores them against reference captions/
headers plus some keyword and structural heuristics, then maps columns into
a parameter schema. No LLM or API key needed.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import shutil
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

from bs4 import BeautifulSoup

MODULE_DIR = Path(__file__).resolve().parent
REFERENCE_FILE = MODULE_DIR / "parameter_table_references.json"


@dataclass
class ParameterRecord:
    pmid: str
    table_id: str
    parameter_name: str
    parameter_symbol: str
    value: str
    unit: str
    uncertainty: str


@dataclass
class TableDecision:
    pmid: str
    table_id: str
    caption: str
    headers: str
    caption_similarity: float
    header_similarity: float
    keyword_score: float
    numeric_density: float
    symbol_density: float
    negative_score: float
    final_score: float
    is_parameter_table: bool
    extracted_rows: int


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("−", "-").replace("–", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalized_text(value: object) -> str:
    return clean_text(value).casefold()


def tokenize(text: str) -> list[str]:
    pattern = (
        r"[a-zA-Z]+(?:_\d+|\d+)?|"
        r"[αβγδεζηθικλμνξοπρστυφχψω]|"
        r"\d+(?:\.\d+)?"
    )
    return re.findall(pattern, normalized_text(text))


def term_frequency(tokens: Sequence[str]) -> Counter[str]:
    counts = Counter(tokens)
    total = sum(counts.values())
    if not total:
        return Counter()
    return Counter({t: c / total for t, c in counts.items()})


def cosine_similarity(text_a: str, text_b: str) -> float:
    vec_a = term_frequency(tokenize(text_a))
    vec_b = term_frequency(tokenize(text_b))
    if not vec_a or not vec_b:
        return 0.0

    shared = set(vec_a) & set(vec_b)
    dot = sum(vec_a[t] * vec_b[t] for t in shared)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def maximum_similarity(text: str, references: Iterable[str]) -> float:
    normalized = clean_text(text)
    if not normalized:
        return 0.0

    candidates = {normalized}
    for fragment in re.split(r"[\n.;:]+", normalized):
        fragment = clean_text(fragment)
        if fragment:
            candidates.add(fragment)

    # also try n-gram windows so partial header/caption matches count
    tokens = tokenize(normalized)
    for window in range(2, min(9, len(tokens) + 1)):
        for start in range(len(tokens) - window + 1):
            candidates.add(" ".join(tokens[start:start + window]))

    return max(
        (cosine_similarity(c, r) for c in candidates for r in references),
        default=0.0,
    )


def load_references() -> dict:
    with REFERENCE_FILE.open(encoding="utf-8") as f:
        return json.load(f)


def extract_caption(table, table_number: int) -> str:
    caption_tag = table.find("caption")
    if caption_tag:
        return clean_text(caption_tag.get_text(" ", strip=True))

    previous = table.find_previous(["p", "div", "h1", "h2", "h3", "h4"])
    if previous:
        candidate = clean_text(previous.get_text(" ", strip=True))
        if len(candidate) <= 1000:
            return candidate

    return f"Table {table_number}"


def extract_table_matrix(table) -> list[list[str]]:
    matrix: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = tr.find_all(["th", "td"])
        row = [clean_text(cell.get_text(" ", strip=True)) for cell in cells]
        if any(row):  # keep blanks, column position still matters
            matrix.append(row)
    return matrix


HEADER_TERMS = {
    "parameter", "symbol", "description", "definition", "meaning",
    "value", "estimate", "unit", "uncertainty", "standard deviation", "range",
}


def separate_headers(table, matrix: list[list[str]]) -> tuple[list[str], list[list[str]]]:
    if not matrix:
        return [], []

    first_tr = table.find("tr")
    has_th = bool(first_tr and first_tr.find_all("th"))
    first_row_text = normalized_text(" ".join(matrix[0]))
    resembles_header = has_th or any(t in first_row_text for t in HEADER_TERMS)

    if resembles_header:
        return matrix[0], matrix[1:]
    return [], matrix


def numeric_density(rows: Sequence[Sequence[str]]) -> float:
    nonempty = numeric = 0
    for row in rows:
        for cell in row:
            text = clean_text(cell)
            if not text:
                continue
            nonempty += 1
            if re.search(r"[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", text):
                numeric += 1
    return numeric / nonempty if nonempty else 0.0


SYMBOL_PATTERN = re.compile(
    r"^(?:"
    r"[a-zA-Z](?:_\{?[a-zA-Z0-9]+\}?)?"
    r"|[a-zA-Z]\d+"
    r"|alpha|beta|gamma|delta|lambda|mu|sigma|theta|rho"
    r"|[αβγδεζηθικλμνξοπρστυφχψω]"
    r")$",
    re.IGNORECASE,
)


def looks_like_symbol(value: str) -> bool:
    text = normalized_text(value).replace(" ", "")
    if not text or len(text) > 20:
        return False
    return bool(SYMBOL_PATTERN.match(text))



def split_parameter_cell(text: str) -> tuple[str, str]:
    """Split a combined parameter cell into symbol and name.

    Examples:
        β (transmission rate)
        beta - transmission rate
        gamma: recovery rate
        sigma incubation rate
    """

    raw = clean_text(text)

    if not raw:
        return "", ""

    # Example: β (transmission rate)
    match = re.match(
        r"^\s*"
        r"([A-Za-zα-ωΑ-Ω\\][A-Za-z0-9_{}\\]*)"
        r"\s*\((.+)\)\s*$",
        raw,
    )

    if match:
        symbol = clean_text(match.group(1))
        name = clean_text(match.group(2))
        return symbol, name

    # Examples:
    # beta - transmission rate
    # gamma: recovery rate
    # sigma = progression rate
    match = re.match(
        r"^\s*"
        r"([A-Za-zα-ωΑ-Ω\\][A-Za-z0-9_{}\\]*)"
        r"\s*[:\-–—=]\s*(.+)$",
        raw,
    )

    if match:
        symbol = clean_text(match.group(1))
        name = clean_text(match.group(2))
        return symbol, name

    # Example: sigma incubation rate
    match = re.match(
        r"^\s*"
        r"([A-Za-zα-ωΑ-Ω\\][A-Za-z0-9_{}\\]*)"
        r"\s+(.+)$",
        raw,
    )

    if match:
        candidate_symbol = clean_text(match.group(1))
        candidate_name = clean_text(match.group(2))

        if looks_like_symbol(candidate_symbol):
            return candidate_symbol, candidate_name

    # The complete cell contains only a symbol.
    if looks_like_symbol(raw):
        return raw, ""

    # Otherwise, treat the complete cell as a parameter name.
    return "", raw


def symbol_density(rows: Sequence[Sequence[str]]) -> float:
    first_cells = [row[0] for row in rows if row and clean_text(row[0])]
    if not first_cells:
        return 0.0
    return sum(looks_like_symbol(c) for c in first_cells) / len(first_cells)


def keyword_score(text: str) -> float:
    keywords = {
        "parameter", "parameters", "value", "values", "estimate", "estimated",
        "constant", "rate", "kinetic", "initial value", "symbol", "unit",
    }
    normalized = normalized_text(text)
    matches = sum(k in normalized for k in keywords)
    return min(matches / 5.0, 1.0)


def negative_keyword_score(text: str, references: dict) -> float:
    normalized = normalized_text(text)
    matches = sum(k.casefold() in normalized for k in references["negative_keywords"])
    return min(matches / 3.0, 1.0)


def classify_table(caption, headers, rows, references) -> dict:
    header_text = " ".join(headers)
    combined = f"{caption} {header_text}"

    caption_similarity = maximum_similarity(caption, references["caption_references"])
    header_similarity = maximum_similarity(header_text, references["header_references"])
    positive_score = keyword_score(combined)
    number_score = numeric_density(rows)
    parameter_symbol_score = symbol_density(rows)
    negative_score = negative_keyword_score(combined, references)

    final_score = (
        0.30 * caption_similarity
        + 0.25 * header_similarity
        + 0.20 * positive_score
        + 0.15 * number_score
        + 0.10 * parameter_symbol_score
        - 0.20 * negative_score
    )
    final_score = min(max(final_score, 0.0), 1.0)
    threshold = references["classification_threshold"]

    return {
        "caption_similarity": round(caption_similarity, 4),
        "header_similarity": round(header_similarity, 4),
        "keyword_score": round(positive_score, 4),
        "numeric_density": round(number_score, 4),
        "symbol_density": round(parameter_symbol_score, 4),
        "negative_score": round(negative_score, 4),
        "final_score": round(final_score, 4),
        "is_parameter_table": final_score >= threshold,
    }


def header_alias_score(
    header: str,
    alias: str,
) -> float:
    """Score how well one table header matches one configured alias."""

    header_text = normalized_text(header)
    alias_text = normalized_text(alias)

    if not header_text or not alias_text:
        return 0.0

    # Exact normalized matches are strongest.
    if header_text == alias_text:
        return 1.0

    # A full alias appearing in a longer header is also strong.
    if alias_text in header_text:
        return 0.95

    # Use cosine similarity only as a weaker fallback.
    return cosine_similarity(header_text, alias_text)


def find_best_unused_column(
    headers: Sequence[str],
    aliases: Sequence[str],
    used_columns: set[int],
) -> tuple[int | None, float]:
    """Find the best available column for one standardized field."""

    best_index = None
    best_score = 0.0

    for index, header in enumerate(headers):
        if index in used_columns:
            continue

        score = max(
            (
                header_alias_score(header, alias)
                for alias in aliases
            ),
            default=0.0,
        )

        if score > best_score:
            best_index = index
            best_score = score

    # Require a reasonably strong header match.
    if best_score < 0.60:
        return None, best_score

    return best_index, best_score


def map_columns(
    headers: Sequence[str],
    aliases: dict,
) -> dict[str, int | None]:
    """Map source columns to unique standardized parameter fields.

    Each source column can be assigned to only one output field.
    """

    mappings: dict[str, int | None] = {
        "parameter_symbol": None,
        "parameter_name": None,
        "value": None,
        "unit": None,
        "uncertainty": None,
    }

    used_columns: set[int] = set()

    # The ordering matters. Value is mapped before unit and uncertainty,
    # while symbol and name are kept distinct.
    field_order = [
        "parameter_symbol",
        "parameter_name",
        "value",
        "unit",
        "uncertainty",
    ]

    for field in field_order:
        index, _score = find_best_unused_column(
            headers,
            aliases.get(field, []),
            used_columns,
        )

        mappings[field] = index

        if index is not None:
            used_columns.add(index)

    return mappings


def cell_contains_number(value: str) -> bool:
    """Return True if a cell contains a numeric value."""

    text = clean_text(value)

    if not text:
        return False

    return bool(
        re.search(
            r"[<>≤≥]?\s*[+-]?\d+(?:\.\d+)?"
            r"(?:[eE][+-]?\d+)?",
            text,
        )
    )


def column_numeric_ratio(
    rows: Sequence[Sequence[str]],
    column_index: int | None,
) -> float:
    """Calculate the proportion of nonempty cells containing numbers."""

    if column_index is None:
        return 0.0

    nonempty = 0
    numeric = 0

    for row in rows:
        if column_index >= len(row):
            continue

        cell = clean_text(row[column_index])

        if not cell:
            continue

        nonempty += 1

        if cell_contains_number(cell):
            numeric += 1

    return numeric / nonempty if nonempty else 0.0


def find_numeric_value_column(
    rows: Sequence[Sequence[str]],
    excluded_columns: set[int],
) -> int | None:
    """Find the most numeric column not used for symbol or name."""

    maximum_width = max(
        (len(row) for row in rows),
        default=0,
    )

    best_index = None
    best_ratio = 0.0

    for index in range(maximum_width):
        if index in excluded_columns:
            continue

        ratio = column_numeric_ratio(rows, index)

        if ratio > best_ratio:
            best_index = index
            best_ratio = ratio

    # Avoid selecting mostly textual columns as values.
    if best_ratio < 0.40:
        return None

    return best_index


NUMBER_PATTERN = re.compile(r"[<>≤≥]?\s*[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")


def split_value_unit_uncertainty(text: str) -> tuple[str, str, str]:
    raw = clean_text(text)
    if not raw:
        return "", "", ""

    number_match = NUMBER_PATTERN.search(raw)
    if not number_match:
        return raw, "", ""

    value = number_match.group(0).replace(" ", "")
    remainder = raw[number_match.end():].strip()

    uncertainty = ""
    uncertainty_match = re.search(
        r"(?:±\s*[+-]?\d+(?:\.\d+)?)|(?:\[[^\]]+\])|(?:\([^\)]+\))", remainder
    )
    if uncertainty_match:
        uncertainty = clean_text(uncertainty_match.group(0))
        remainder = (
            remainder[:uncertainty_match.start()] + " " + remainder[uncertainty_match.end():]
        ).strip()

    return value, clean_text(remainder), uncertainty


def get_cell(row: Sequence[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return clean_text(row[index])


def extract_records(pmid, table_id, headers, rows, aliases) -> list[ParameterRecord]:
    if not rows:
        return []

    mappings = map_columns(headers, aliases)


    # Prevent the parameter-name or symbol column from being
    # incorrectly used as the numerical value column.
    identity_columns = {
        index
        for index in (
            mappings.get("parameter_symbol"),
            mappings.get("parameter_name"),
        )
        if index is not None
    }

    mapped_value_index = mappings.get("value")
    mapped_value_numeric_ratio = column_numeric_ratio(
        rows,
        mapped_value_index,
    )

    if (
        mapped_value_index in identity_columns
        or mapped_value_numeric_ratio < 0.40
    ):
        mappings["value"] = find_numeric_value_column(
            rows,
            excluded_columns=identity_columns,
        )
    if not headers:
        # no reliable header row, just guess positions from column count
        width = max(len(row) for row in rows)
        if width >= 3:
            mappings = {
                "parameter_symbol": 0,
                "parameter_name": 1,
                "value": 2,
                "unit": 3 if width > 3 else None,
                "uncertainty": 4 if width > 4 else None,
            }
        elif width == 2:
            mappings = {
                "parameter_symbol": 0,
                "parameter_name": None,
                "value": 1,
                "unit": None,
                "uncertainty": None,
            }
        else:
            return []

    records: list[ParameterRecord] = []

    for row in rows:
        symbol = get_cell(row, mappings.get("parameter_symbol"))
        name = get_cell(row, mappings.get("parameter_name"))
        raw_value = get_cell(row, mappings.get("value"))
        unit = get_cell(row, mappings.get("unit"))
        uncertainty = get_cell(row, mappings.get("uncertainty"))

        if not raw_value:
            continue

        parsed_value, parsed_unit, parsed_uncertainty = split_value_unit_uncertainty(raw_value)
        unit = unit or parsed_unit
        uncertainty = uncertainty or parsed_uncertainty

        if name and symbol and normalized_text(name) == normalized_text(symbol):
            name = ""  # don't duplicate the symbol as its own description

        if not symbol and not name:
            continue

        # Correct symbol-only parameter cells.
        #
        # A generic header such as "Parameter" may be mapped to
        # parameter_name even when the cells contain only symbols
        # such as beta, gamma, β, σ, or \delta_I.
        if name and looks_like_symbol(name):
            if not symbol:
                symbol = name

            name = ""

        # Also use split_parameter_cell() to distinguish:
        # β                     -> symbol only
        # β (transmission rate) -> symbol plus name
        # transmission rate     -> name only
        if name:
            inferred_symbol, inferred_name = split_parameter_cell(name)

            if inferred_symbol and inferred_name:
                if not symbol:
                    symbol = inferred_symbol

                name = inferred_name

            elif inferred_symbol and not inferred_name:
                if not symbol:
                    symbol = inferred_symbol

                name = ""

        # Never write the same symbol into both output fields.
        if (
            symbol
            and name
            and normalized_text(symbol) == normalized_text(name)
        ):
            name = ""

        records.append(ParameterRecord(
            pmid=pmid,
            table_id=table_id,
            parameter_name=name,
            parameter_symbol=symbol,
            value=parsed_value,
            unit=unit,
            uncertainty=uncertainty,
        ))

    return records


def write_dict_rows(path: Path, rows: Sequence[dict], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def process_collection(input_dir: Path, output_dir: Path) -> None:
    references = load_references()
    extracted_dir = output_dir / "extracted_tables"
    extracted_dir.mkdir(parents=True, exist_ok=True)

    decisions: list[dict] = []
    observed_headers: list[dict] = []
    summaries: list[dict] = []

    html_files = sorted(input_dir.rglob("*.html"))

    for paper_index, html_path in enumerate(html_files, start=1):
        pmid = html_path.stem
        html = html_path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")

        paper_records: list[ParameterRecord] = []
        tables = soup.find_all("table")

        for table_number, table in enumerate(tables, start=1):
            table_id = f"Table {table_number}"
            caption = extract_caption(table, table_number)
            matrix = extract_table_matrix(table)
            headers, rows = separate_headers(table, matrix)

            observed_headers.append({
                "pmid": pmid,
                "table_id": table_id,
                "caption": caption,
                "headers": " | ".join(headers),
                "column_count": max((len(r) for r in matrix), default=0),
                "row_count": len(rows),
            })

            scores = classify_table(caption, headers, rows, references)
            records: list[ParameterRecord] = []

            if scores["is_parameter_table"]:
                records = extract_records(pmid, table_id, headers, rows, references["column_aliases"])
                paper_records.extend(records)

            decisions.append(asdict(TableDecision(
                pmid=pmid,
                table_id=table_id,
                caption=caption,
                headers=" | ".join(headers),
                extracted_rows=len(records),
                **scores,
            )))

        output_path = extracted_dir / f"{pmid}_parameters.csv"
        write_dict_rows(
            output_path,
            [asdict(r) for r in paper_records],
            ["pmid", "table_id", "parameter_symbol", "parameter_name", "value", "unit", "uncertainty"],
        )

        summaries.append({
            "pmid": pmid,
            "tables_found": len(tables),
            "parameter_rows_extracted": len(paper_records),
            "status": "extracted" if paper_records else "needs_review",
        })

        print(f"[{paper_index}/{len(html_files)}] {pmid}: {len(tables)} tables, {len(paper_records)} parameter rows")

    write_dict_rows(
        output_dir / "table_classification_results.csv",
        decisions,
        list(TableDecision.__dataclass_fields__),
    )
    write_dict_rows(
        output_dir / "observed_headers.csv",
        observed_headers,
        ["pmid", "table_id", "caption", "headers", "column_count", "row_count"],
    )
    write_dict_rows(
        output_dir / "extraction_summary.csv",
        summaries,
        ["pmid", "tables_found", "parameter_rows_extracted", "status"],
    )

    shutil.copy2(REFERENCE_FILE, output_dir / "reference_snapshot.json")

    print()
    print(f"Papers processed: {len(html_files)}")
    print(f"Output directory: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract parameter tables from Marker HTML without an LLM.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    process_collection(args.input_dir.expanduser(), args.output_dir.expanduser())


if __name__ == "__main__":
    main()
