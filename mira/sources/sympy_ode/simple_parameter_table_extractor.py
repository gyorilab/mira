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
    is_sensitivity_table: bool
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
    """Split a cell containing BOTH a parameter symbol and description.

    Examples that may be split:
        "β - Transmission rate"
        "mu: natural mortality rate"

    Ordinary hyphenated descriptive words such as:
        "Disease-induced death rate"
        "age-specific mortality"
        "time-dependent transmission"

    must remain intact.
    """

    raw = clean_text(text)

    if not raw:
        return "", ""

    # Only recognize separators surrounded by whitespace.
    #
    # This allows:
    #     β - Transmission rate
    #
    # but prevents:
    #     Disease-induced death rate
    #
    # from being split.
    separator_match = re.match(
        r"^\s*(.+?)\s+(?:-|–|—)\s+(.+?)\s*$",
        raw,
    )

    if separator_match:
        possible_symbol = clean_text(
            separator_match.group(1)
        )
        possible_name = clean_text(
            separator_match.group(2)
        )

        # The left side must actually look symbol-like.
        #
        # Avoid treating normal words such as "Disease" as symbols.
        if (
            possible_symbol
            and len(possible_symbol.split()) <= 2
            and len(possible_symbol) <= 20
        ):
            return possible_symbol, possible_name

    # Also support a conservative colon form:
    #     β: Transmission rate
    colon_match = re.match(
        r"^\s*(.{1,20}?)\s*:\s+(.+?)\s*$",
        raw,
    )

    if colon_match:
        possible_symbol = clean_text(
            colon_match.group(1)
        )
        possible_name = clean_text(
            colon_match.group(2)
        )

        if (
            possible_symbol
            and len(possible_symbol.split()) <= 2
        ):
            return possible_symbol, possible_name

    # No safe symbol/name split identified.
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


def is_sensitivity_analysis_table(
    caption: str,
    headers: Sequence[str],
    references: dict,
) -> bool:
    """Detect tables whose numerical columns are sensitivity metrics.

    A parameter-value table is not rejected merely because its caption
    says that the values were used for sensitivity analysis.
    """

    caption_text = normalized_text(caption)
    header_text = normalized_text(" ".join(headers))
    combined_text = f"{caption_text} {header_text}".strip()

    # Strong sensitivity-result indicators.
    # These describe the actual numerical contents of a table.
    sensitivity_metric_phrases = (
        "sensitivity index",
        "sensitivity indices",
        "normalized sensitivity index",
        "normalized sensitivity indices",
        "sensitivity coefficient",
        "sensitivity coefficients",
        "partial rank correlation coefficient",
        "partial rank correlation coefficients",
        "rank correlation coefficient",
        "rank correlation coefficients",
        "prcc",
        "sobol index",
        "sobol indices",
        "morris index",
        "morris indices",
        "elasticity index",
        "elasticity indices",
        "elasticity coefficient",
        "elasticity coefficients",
    )

    if any(
        phrase in header_text
        for phrase in sensitivity_metric_phrases
    ):
        return True

    # Also reject when a sensitivity-analysis caption is paired with
    # a generic metric/result column. The caption alone is insufficient.
    sensitivity_caption = any(
        phrase in caption_text
        for phrase in (
            "sensitivity analysis results",
            "results of sensitivity analysis",
            "sensitivity indices",
            "sensitivity index",
            "parameter sensitivity results",
            "partial rank correlation coefficient",
            "partial rank correlation coefficients",
            "prcc",
            "eprcc",
        )
    )

    # PRCC/ePRCC explicitly identify sensitivity-analysis result tables.
    # These tables can have model variables as column headers rather than
    # generic headers such as "coefficient" or "correlation".
    explicit_sensitivity_metric = any(
        phrase in caption_text
        for phrase in (
            "partial rank correlation coefficient",
            "partial rank correlation coefficients",
            "prcc",
            "eprcc",
        )
    )

    if explicit_sensitivity_metric:
        return True

    metric_headers = (
        "index",
        "coefficient",
        "correlation",
        "rank",
        "prcc",
        "sobol",
        "morris",
        "elasticity",
    )

    has_metric_header = any(
        metric in header_text
        for metric in metric_headers
    )

    # Genuine parameter-value headers override sensitivity wording
    # appearing incidentally in the caption.
    parameter_value_headers = (
        "fitted value",
        "estimated value",
        "parameter value",
        "initial value",
        "baseline value",
        "default value",
        "value range",
        "values range",
        "value ranges",
        "values ranges",
    )

    has_parameter_value_header = any(
        phrase in header_text
        for phrase in parameter_value_headers
    )

    if has_parameter_value_header:
        return False

    return sensitivity_caption and has_metric_header


def is_parameter_matrix_table(
    headers: list[str],
    rows: list[list[str]],
) -> bool:
    """Detect column-oriented parameter/scenario matrices.

    These are tables where many parameters are spread horizontally
    across columns and rows describe things such as lower bound,
    upper bound, initial value, final value, IFR, or R0.

    The simple extractor instead targets one parameter per row.
    """

    if not headers or not rows:
        return False

    normalized_headers = [
        normalized_text(header)
        for header in headers
    ]

    row_width = max(
        (len(row) for row in rows),
        default=0,
    )

    # Use both the parsed header width and row width.
    # Some HTML tables have wide headers but rows may be temporarily
    # truncated/irregular during parsing or testing.
    table_width = max(
        len(headers),
        row_width,
    )

    # Do not reject ordinary narrow parameter tables.
    if table_width < 6:
        return False

    scenario_terms = {
        "lower bound",
        "upper bound",
        "initial value",
        "final value",
        "final value (*)",
        "ifr",
        "r0",
        "r 0",
        "basic reproduction number",
    }

    scenario_rows = 0

    for row in rows[:50]:
        first_cells = [
            normalized_text(cell)
            for cell in row[:3]
            if clean_text(cell)
        ]

        if any(
            cell in scenario_terms
            for cell in first_cells
        ):
            scenario_rows += 1

    # Count short non-generic headers. In matrix tables these are
    # commonly individual parameters such as alpha1, beta1, q, E(0).
    generic_headers = {
        "",
        "case",
        "variable",
        "variables",
        "name",
        "description",
        "definition",
        "parameter",
        "parameters",
        "value",
        "values",
        "unit",
        "units",
        "uncertainty",
        "source",
        "data source",
        "prior",
    }

    possible_parameter_columns = 0

    for header in normalized_headers:
        if (
            header
            and header not in generic_headers
            and len(header) <= 25
        ):
            possible_parameter_columns += 1

    return (
        scenario_rows >= 2
        and possible_parameter_columns >= 3
    )


def is_parameter_definition_table(
    caption: str,
    headers: list[str],
    rows: list[list[str]],
) -> bool:
    """Detect simple symbol/parameter-definition companion tables.

    These tables may contain no numerical values, but can still be useful
    when another table in the same PMID provides the parameter values.
    """

    if not headers or not rows:
        return False

    caption_text = normalized_text(caption)
    normalized_headers = [
        normalized_text(header)
        for header in headers
    ]

    combined_headers = " ".join(normalized_headers)

    symbol_header_terms = (
        "parameter",
        "variable",
        "symbol",
        "name",
    )

    definition_header_terms = (
        "definition",
        "description",
        "meaning",
        "interpretation",
    )

    has_symbol_header = any(
        term in combined_headers
        for term in symbol_header_terms
    )

    has_definition_header = any(
        term in combined_headers
        for term in definition_header_terms
    )

    definition_caption_terms = (
        "description of parameters",
        "description of the parameters",
        "description of fixed parameters",
        "description of the fixed parameters",
        "definition of parameters",
        "definitions of parameters",
        "variables and parameters",
        "parameter definitions",
    )

    caption_supports_definition = any(
        term in caption_text
        for term in definition_caption_terms
    )

    # Count rows that contain at least two meaningful cells.
    # This helps reject captions or malformed one-cell fragments.
    nonempty_rows = 0

    for row in rows:
        nonempty = [
            clean_text(cell)
            for cell in row
            if clean_text(cell)
        ]

        if len(nonempty) >= 2:
            nonempty_rows += 1

    if nonempty_rows < 2:
        return False

    # Normal case:
    # recognizable symbol/parameter header plus a definition signal.
    if (
        has_symbol_header
        and (
            has_definition_header
            or caption_supports_definition
        )
    ):
        return True

    # Marker can occasionally corrupt or merge the header row.
    # In that case, a strong parameter-definition caption is enough
    # to make the table a DEFINITION CANDIDATE.
    #
    # It is still not automatically selected: downstream symbol-overlap
    # matching must confirm that it corresponds to an already selected
    # parameter/value table from the same PMID.
    if caption_supports_definition:
        return True

    return False


def extract_first_column_symbols(
    rows: list[list[str]],
) -> set[str]:
    """Collect non-empty first-column entries for overlap matching."""

    symbols: set[str] = set()

    for row in rows:
        if not row:
            continue

        value = clean_text(row[0])

        if value:
            symbols.add(value)

    return symbols


def symbol_overlap_fraction(
    symbols_a: set[str],
    symbols_b: set[str],
) -> float:
    """Return overlap relative to the smaller non-empty symbol set."""

    if not symbols_a or not symbols_b:
        return 0.0

    intersection = symbols_a & symbols_b
    denominator = min(
        len(symbols_a),
        len(symbols_b),
    )

    if denominator == 0:
        return 0.0

    return len(intersection) / denominator


def classify_table(caption, headers, rows, references) -> dict:
    header_text = " ".join(headers)
    combined = f"{caption} {header_text}"

    caption_similarity = maximum_similarity(caption, references["caption_references"])
    header_similarity = maximum_similarity(header_text, references["header_references"])
    positive_score = keyword_score(combined)
    number_score = numeric_density(rows)
    parameter_symbol_score = symbol_density(rows)
    negative_score = negative_keyword_score(combined, references)

    sensitivity_table = is_sensitivity_analysis_table(
        caption,
        headers,
        references,
    )

    # Reject complex column-oriented parameter/scenario matrices.
    parameter_matrix_table = is_parameter_matrix_table(
        headers,
        rows,
    )

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
        "is_parameter_table": (

            final_score >= threshold

            and not sensitivity_table

            and not parameter_matrix_table

        ),

        "is_sensitivity_table": sensitivity_table,
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
    """Return True when a cell contains a scalar, fraction, or range."""

    text = clean_text(value)

    if not text:
        return False

    return bool(NUMBER_PATTERN.search(text))

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


NUMBER_PATTERN = re.compile(
    r"[<>≤≥]?\s*[+-]?"
    r"(?:"
    # Fraction: 1/21, 1 / 21, 3.5/7
    r"(?:"
    r"(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
    r"\s*/\s*"
    r"(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
    r")"
    r"|"
    # Ordinary number: 123,456; 12345; 1.23e-6
    r"(?:"
    r"\d{1,3}(?:,\d{3})+"
    r"|\d{1,3}(?:\s\d{3})+"
    r"|\d+"
    r")"
    r"(?:\.\d+)?"
    r"(?:[eE][+-]?\d+)?"
    r")"
)


def split_value_unit_uncertainty(
    text: str,
) -> tuple[str, str, str]:
    """Separate a value expression, unit, and uncertainty safely.

    Mathematical expressions are preserved, including:

        1/21
        1/(70*360)
        2*(1/21)
        exp(-kt)
        1.2e-5
        2 × 10^-5

    A unit is removed only when it appears as a recognizable suffix.
    """

    raw = clean_text(text)

    if not raw:
        return "", "", ""

    value_text = raw
    uncertainty = ""
    unit = ""

    # -------------------------------------------------------------
    # 1. Extract bracketed uncertainty only when it follows a value.
    #
    # Examples:
    #   1.30 [1.21-1.39]
    #   2.95 (2.83-3.33)
    #
    # Parentheses belonging to a mathematical expression, such as
    # 1/(70*360), are not treated as uncertainty.
    # -------------------------------------------------------------

    bracket_match = re.search(
        r"\s+"
        r"(?P<uncertainty>"
        r"\[[^\[\]]+\]"
        r"|"
        r"\((?:[^()]|\([^()]*\))+\)"
        r")"
        r"(?=\s*(?:[A-Za-z%°µμ]|$))",
        value_text,
    )

    if bracket_match:
        candidate = clean_text(
            bracket_match.group("uncertainty")
        )

        # Treat it as uncertainty only if it contains a numeric
        # range, ± value, CI-like content, or multiple numeric values.
        numeric_items = re.findall(
            r"[+-]?\d+(?:\.\d+)?",
            candidate,
        )

        uncertainty_signals = (
            "±" in candidate
            or re.search(
                r"\d\s*(?:-|–|—|to)\s*\d",
                candidate,
                flags=re.IGNORECASE,
            )
            or len(numeric_items) >= 2
        )

        if uncertainty_signals:
            uncertainty = candidate

            value_text = clean_text(
                value_text[: bracket_match.start()]
                + " "
                + value_text[bracket_match.end() :]
            )

    # -------------------------------------------------------------
    # 2. Extract plus/minus uncertainty.
    #
    # Example:
    #   0.42 ± 0.05 day^-1
    # -------------------------------------------------------------

    plus_minus_match = re.search(
        r"\s*(?P<uncertainty>±\s*"
        r"[+-]?\d+(?:\.\d+)?"
        r"(?:[eE][+-]?\d+)?)",
        value_text,
    )

    if plus_minus_match:
        uncertainty = clean_text(
            plus_minus_match.group("uncertainty")
        )

        value_text = clean_text(
            value_text[: plus_minus_match.start()]
            + " "
            + value_text[plus_minus_match.end() :]
        )

    # -------------------------------------------------------------
    # 3. Recognize a unit only at the END of the cell.
    #
    # A whitespace boundary is required before most units. Therefore:
    #
    #   1/(70*360)       remains a complete value
    #   1/(70*360) day^-1 separates into value and unit
    # -------------------------------------------------------------

    unit_suffix_pattern = re.compile(
        r"""
        
        (?P<prefix>\s+)
        (?P<unit>
            (?:
                day|days|d|
                week|weeks|wk|wks|
                month|months|mo|
                year|years|yr|yrs|
                hour|hours|hr|hrs|h|
                minute|minutes|min|
                second|seconds|sec|s|
                person|persons|people|
                individual|individuals|
                patient|patients|
                cell|cells|
                copy|copies|
                dose|doses|
                case|cases|
                event|events|
                kg|g|mg|ug|µg|μg|ng|
                l|ml|ul|µl|μl|
                m|cm|mm|um|µm|μm|nm|
                mol|mmol|umol|µmol|μmol|nmol|
                mM|uM|µM|μM|nM|
                percent|percentage|
                probability|
                dimensionless
            )
            (?:
                \s*
                (?:
                    \^?\s*\{?\s*[+-]?\d+\s*\}?
                    |
                    [⁻−-][¹²³⁴⁵⁶⁷⁸⁹⁰]+
                )
            )?
            (?:
                \s*/\s*
                (?:
                    day|days|d|
                    week|weeks|
                    month|months|
                    year|years|
                    hour|hours|h|
                    minute|minutes|min|
                    second|seconds|s|
                    person|people|
                    cell|cells|
                    kg|g|mg|ml|l
                )
            )?
        )
        \s*$
        """,
        flags=re.IGNORECASE | re.VERBOSE,
    )

    unit_match = unit_suffix_pattern.search(value_text)

    if unit_match:
        unit = clean_text(unit_match.group("unit"))
        value_text = clean_text(
            value_text[: unit_match.start()]
        )

    # Percent signs may directly follow a value without whitespace.
    percent_match = re.search(
        r"(?P<unit>%|‰)\s*$",
        value_text,
    )

    if percent_match:
        unit = percent_match.group("unit")
        value_text = clean_text(
            value_text[: percent_match.start()]
        )

    # -------------------------------------------------------------
    # 4. Return the complete remaining expression as the value.
    # -------------------------------------------------------------

    value = clean_text(value_text)

    return value, unit, uncertainty

def get_cell(row: Sequence[str], index: int | None) -> str:
    if index is None or index >= len(row):
        return ""
    return clean_text(row[index])



def merge_parameter_continuation_rows(
    rows: list[list[str]],
    mappings: dict[str, int | None],
) -> list[list[str]]:
    """Merge physical HTML rows belonging to one logical parameter.

    Handles tables such as:

        psi_H | Modification parameter for infection rate | ""
              | of high risk susceptible individuals      | 1.2-2

    which should become one logical row:

        psi_H | Modification parameter for infection rate
                of high risk susceptible individuals      | 1.2-2
    """

    if not rows:
        return rows

    symbol_index = mappings.get("parameter_symbol")
    name_index = mappings.get("parameter_name")
    value_index = mappings.get("value")
    unit_index = mappings.get("unit")
    uncertainty_index = mappings.get("uncertainty")

    def cell(row, index):
        if index is None:
            return ""
        if index < 0 or index >= len(row):
            return ""
        return clean_text(row[index])

    def ensure_width(row, width):
        row = list(row)
        if len(row) < width:
            row.extend([""] * (width - len(row)))
        return row

    width = max((len(row) for row in rows), default=0)

    merged: list[list[str]] = []

    for original_row in rows:
        current = ensure_width(original_row, width)

        current_symbol = cell(current, symbol_index)
        current_name = cell(current, name_index)
        current_value = cell(current, value_index)

        if merged:
            previous = merged[-1]

            previous_symbol = cell(previous, symbol_index)
            previous_name = cell(previous, name_index)
            previous_value = cell(previous, value_index)

            # Continuation-row pattern:
            #
            # previous:
            #   symbol/name present, but value absent
            #
            # current:
            #   symbol absent, description continues,
            #   and value appears on this second physical row
            continuation = (
                not current_symbol
                and bool(current_name)
                and bool(current_value)
                and bool(previous_symbol or previous_name)
                and not previous_value
            )

            if continuation:
                # Join the definition text.
                if name_index is not None:
                    pieces = [
                        part
                        for part in (
                            previous_name,
                            current_name,
                        )
                        if part
                    ]
                    previous[name_index] = clean_text(
                        " ".join(pieces)
                    )

                # Carry value onto the logical parameter row.
                if value_index is not None:
                    previous[value_index] = current_value

                # Carry unit if present.
                if unit_index is not None:
                    current_unit = cell(current, unit_index)

                    if (
                        current_unit
                        and not cell(previous, unit_index)
                    ):
                        previous[unit_index] = current_unit

                # Carry uncertainty if present.
                if uncertainty_index is not None:
                    current_uncertainty = cell(
                        current,
                        uncertainty_index,
                    )

                    if (
                        current_uncertainty
                        and not cell(
                            previous,
                            uncertainty_index,
                        )
                    ):
                        previous[
                            uncertainty_index
                        ] = current_uncertainty

                continue

        merged.append(current)

    return merged


def is_internal_header_row(row: list[str]) -> bool:
    """Return True when a data row is actually a repeated/sub-header row.

    Examples:
        Initial Values | Definitions | Estimated Mean Value |
        Standard Deviation | Data Source

        Parameter | Description | Value | Unit

    These should not become ParameterRecord objects.
    """

    cells = [
        normalized_text(cell)
        for cell in row
        if clean_text(cell)
    ]

    if not cells:
        return False

    header_phrases = {
        "parameter",
        "parameters",
        "parameter symbol",
        "symbol",
        "variable",
        "variables",
        "initial value",
        "initial values",
        "definition",
        "definitions",
        "description",
        "descriptions",
        "value",
        "values",
        "estimated value",
        "estimated mean value",
        "mean value",
        "standard deviation",
        "std deviation",
        "standard error",
        "uncertainty",
        "unit",
        "units",
        "data source",
        "source",
        "references",
        "reference",
        "comments",
    }

    exact_matches = sum(
        cell in header_phrases
        for cell in cells
    )

    # A repeated header normally contains several header-like cells.
    if exact_matches >= 2:
        return True

    # Special case for common internal section headers such as:
    # "Initial Values | Definitions | Estimated Mean Value | ..."
    if (
        any(cell in {"initial value", "initial values"} for cell in cells)
        and any(
            cell in {
                "definition",
                "definitions",
                "description",
                "descriptions",
            }
            for cell in cells
        )
    ):
        return True

    return False


def repair_compound_parameter_header_mapping(
    headers: list[str],
    rows: list[list[str]],
    mappings: dict,
) -> dict:
    """Repair mappings for headers spanning symbol + definition columns.

    Example HTML structure:

        Parameter Definitions   [colspan=2]
        Estimated mean value
        Standard deviation
        Data source

    Physical data columns are actually:

        0 -> parameter symbol
        1 -> parameter definition
        2 -> parameter value
        3 -> uncertainty / standard deviation
        4 -> source

    This prevents the definition column from disappearing and prevents
    the mean-value column from being reused as uncertainty.
    """

    repaired = dict(mappings)

    normalized_headers = [
        normalized_text(header)
        for header in headers
    ]

    joined_headers = " | ".join(
        normalized_headers
    )

    row_width = max(
        (len(row) for row in rows),
        default=0,
    )

    has_parameter_definitions = (
        "parameter definitions" in joined_headers
        or "parameter definition" in joined_headers
    )

    has_mean_value = any(
        phrase in joined_headers
        for phrase in (
            "estimated mean value",
            "estimated value",
            "mean value",
        )
    )

    has_standard_deviation = any(
        phrase in joined_headers
        for phrase in (
            "standard deviation",
            "std deviation",
        )
    )

    # This is the key colspan pattern:
    #
    # Parameter Definitions spans the first TWO physical columns.
    #
    # Only apply the override when the table really has enough
    # physical columns to support this interpretation.
    if (
        has_parameter_definitions
        and has_mean_value
        and has_standard_deviation
        and row_width >= 5
    ):
        repaired["parameter_symbol"] = 0
        repaired["parameter_name"] = 1
        repaired["value"] = 2
        repaired["uncertainty"] = 3

        # There is no unit column in this header structure.
        if "unit" in repaired:
            repaired["unit"] = None

    return repaired


def repair_blank_symbol_header_mapping(
    headers: list[str],
    rows: list[list[str]],
    mappings: dict,
) -> dict:
    """Infer a parameter-symbol column when its header is blank.

    Example:

        "" | Epidemiological Meaning | Best-fit Value |
        95% Credible Interval | Prior

    with rows such as:

        beta | Transmission rate | 9.906e-8 | (...) | U(...)

    should map physical column 0 to parameter_symbol.
    """

    repaired = dict(mappings)

    if not headers or not rows:
        return repaired

    normalized_headers = [
        normalized_text(header)
        for header in headers
    ]

    first_header_blank = (
        len(normalized_headers) >= 1
        and not normalized_headers[0]
    )

    joined_headers = " | ".join(normalized_headers)

    has_definition_header = any(
        phrase in joined_headers
        for phrase in (
            "epidemiological meaning",
            "description",
            "definition",
            "parameter name",
            "meaning",
        )
    )

    has_value_header = any(
        phrase in joined_headers
        for phrase in (
            "best fit value",
            "best-fit value",
            "estimated value",
            "mean value",
            "value",
        )
    )

    if not (
        first_header_blank
        and has_definition_header
        and has_value_header
    ):
        return repaired

    # Examine the first physical column.
    first_column = []

    for row in rows[:20]:
        if row:
            value = clean_text(row[0])

            if value:
                first_column.append(value)

    if not first_column:
        return repaired

    # Most symbol cells should be short and not sentence-like.
    symbol_like = 0

    for value in first_column:
        word_count = len(value.split())

        if (
            len(value) <= 30
            and word_count <= 3
        ):
            symbol_like += 1

    symbol_ratio = (
        symbol_like / len(first_column)
    )

    if symbol_ratio >= 0.7:
        repaired["parameter_symbol"] = 0

    return repaired


def repair_name_as_symbol_header_mapping(
    headers: list[str],
    rows: list[list[str]],
    mappings: dict,
) -> dict:
    """Interpret a generic 'Name' column as parameter_symbol when appropriate.

    Example:

        Name | Description | Value | Units

        beta | Transmission coefficient | 2.55 | day^-1

    In this pattern, 'Name' is the mathematical parameter identifier,
    not the descriptive parameter name.
    """

    repaired = dict(mappings)

    if not headers or not rows:
        return repaired

    normalized_headers = [
        normalized_text(header)
        for header in headers
    ]

    # Need at least:
    # Name | Description | Value
    if len(normalized_headers) < 3:
        return repaired

    first_header = normalized_headers[0]

    joined_headers = " | ".join(normalized_headers)

    has_description = any(
        phrase in joined_headers
        for phrase in (
            "description",
            "definition",
            "meaning",
            "epidemiological meaning",
        )
    )

    has_value = any(
        phrase in joined_headers
        for phrase in (
            "value",
            "values",
            "best fit value",
            "best-fit value",
            "estimated value",
            "estimated mean value",
        )
    )

    # Only apply this rule to a generic leading "Name" header
    # when the rest of the table clearly contains a description
    # and numerical value column.
    if not (
        first_header == "name"
        and has_description
        and has_value
    ):
        return repaired

    first_column = []

    for row in rows[:25]:
        if not row:
            continue

        value = clean_text(row[0])

        if value:
            first_column.append(value)

    if not first_column:
        return repaired

    # Mathematical parameter identifiers are generally short
    # and non-sentence-like.
    symbol_like = 0

    for value in first_column:
        if (
            len(value) <= 40
            and len(value.split()) <= 3
        ):
            symbol_like += 1

    ratio = symbol_like / len(first_column)

    if ratio >= 0.7:
        repaired["parameter_symbol"] = 0

        # Description should remain the descriptive parameter name.
        if len(normalized_headers) > 1:
            repaired["parameter_name"] = 1

    return repaired

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

    # Merge HTML continuation rows before extracting records.
    # Repair compound/spanning header structures before
    # extracting rows. Example:
    #
    # Parameter Definitions [colspan=2]
    # Estimated mean value
    # Standard deviation
    #
    mappings = repair_compound_parameter_header_mapping(
        headers,
        rows,
        mappings,
    )

    mappings = repair_blank_symbol_header_mapping(
        headers,
        rows,
        mappings,
    )

    mappings = repair_name_as_symbol_header_mapping(
        headers,
        rows,
        mappings,
    )

    rows = merge_parameter_continuation_rows(
        rows,
        mappings,
    )

    for row in rows:
        # Skip repeated/sub-header rows inside the same HTML table.
        if is_internal_header_row(row):
            continue
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

    # Preserve complete raw tables that pass the classifier.
    # These are later sent together to the LLM at PMID level.
    selected_tables_dir = output_dir / "selected_tables"
    selected_tables_dir.mkdir(parents=True, exist_ok=True)

    decisions: list[dict] = []
    observed_headers: list[dict] = []
    summaries: list[dict] = []

    html_files = sorted(input_dir.rglob("*.html"))

    for paper_index, html_path in enumerate(html_files, start=1):
        pmid = html_path.stem
        html = html_path.read_text(encoding="utf-8", errors="ignore")
        soup = BeautifulSoup(html, "html.parser")

        paper_records: list[ParameterRecord] = []

        # Complete classifier-approved tables for this PMID.
        # These remain intact even if extract_records() produces
        # zero simple parameter rows.
        selected_tables: list[dict] = []

        # Definition-only tables are collected separately first.
        # We only attach them later when their symbols overlap with
        # already-selected parameter value tables from the same PMID.
        definition_candidates: list[dict] = []

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
                # Preserve the entire original table for later
                # PMID-level multi-table LLM structured extraction.
                selected_tables.append({
                    "pmid": pmid,
                    "table_id": table_id,
                    "caption": caption,
                    "headers": headers,
                    "rows": rows,
                })

                # Keep the existing simple deterministic extraction too.
                records = extract_records(
                    pmid,
                    table_id,
                    headers,
                    rows,
                    references["column_aliases"],
                )
                paper_records.extend(records)

            elif is_parameter_definition_table(
                caption,
                headers,
                rows,
            ):
                definition_candidates.append({
                    "pmid": pmid,
                    "table_id": table_id,
                    "caption": caption,
                    "headers": headers,
                    "rows": rows,
                })

            decisions.append(asdict(TableDecision(
                pmid=pmid,
                table_id=table_id,
                caption=caption,
                headers=" | ".join(headers),
                extracted_rows=len(records),
                **scores,
            )))

        # --------------------------------------------------------
        # Attach useful definition-only companion tables.
        #
        # A definition table is preserved only when its first-column
        # symbols overlap substantially with symbols from an already
        # selected parameter table in the same PMID.
        # --------------------------------------------------------
        selected_symbol_sets = [
            extract_first_column_symbols(
                table.get("rows", [])
            )
            for table in selected_tables
        ]

        already_selected_ids = {
            table.get("table_id")
            for table in selected_tables
        }

        for candidate in definition_candidates:
            candidate_id = candidate.get("table_id")

            if candidate_id in already_selected_ids:
                continue

            candidate_symbols = extract_first_column_symbols(
                candidate.get("rows", [])
            )

            best_overlap = max(
                (
                    symbol_overlap_fraction(
                        candidate_symbols,
                        selected_symbols,
                    )
                    for selected_symbols in selected_symbol_sets
                ),
                default=0.0,
            )

            # Require at least moderate symbol agreement.
            # 0.40 allows useful partial definition tables while
            # avoiding unrelated descriptive tables.
            if best_overlap >= 0.40:
                selected_tables.append(candidate)
                already_selected_ids.add(candidate_id)

        # Save all classifier-approved raw tables for this PMID.
        # The structured-output LLM can see them together in one prompt.
        selected_tables_path = (
            selected_tables_dir
            / f"{pmid}_selected_tables.json"
        )

        selected_tables_path.write_text(
            json.dumps(
                {
                    "pmid": pmid,
                    "tables": selected_tables,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

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
        [
            "pmid",
            "table_id",
            "is_parameter_table",
            "is_sensitivity_table",
            "final_score",
            "extracted_rows",
            "caption",
            "headers",
            "caption_similarity",
            "header_similarity",
            "keyword_score",
            "numeric_density",
            "symbol_density",
            "negative_score",
        ],
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
