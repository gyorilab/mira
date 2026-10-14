from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence


PARAMETER_CAPTION_REFERENCES = [
    "model parameters and values",
    "parameter values",
    "estimated parameter values",
    "estimated model parameters",
    "parameter estimates",
    "kinetic parameters",
    "kinetic constants",
    "reaction rate constants",
    "model constants",
    "initial conditions",
    "initial parameter values",
    "parameters used in the model",
    "calibrated parameter values",
    "fitted parameter values",
]

PARAMETER_HEADER_REFERENCES = [
    "parameter symbol description value unit",
    "parameter definition estimate unit",
    "symbol parameter value units",
    "parameter name value",
    "parameter meaning estimated value",
    "parameter initial value unit",
    "symbol description mean standard deviation unit",
]

PARAMETER_KEYWORDS = {
    "parameter", "parameters", "estimate", "estimated", "value", "values",
    "constant", "constants", "coefficient", "coefficients", "rate", "rates",
    "kinetic", "calibrated", "calibration", "fitted", "fitting", "symbol",
    "unit", "units", "initial condition", "initial conditions",
    "initial value", "initial values",
}

NEGATIVE_KEYWORDS = {
    "patient", "patients", "participant", "participants", "demographic",
    "demographics", "baseline characteristics", "clinical characteristics",
    "gene expression", "differential expression", "enrichment", "questionnaire",
    "survey",
}

# Matches things like k_on, Vmax, beta, gamma_1, or a bare greek letter -
# the usual shapes a parameter symbol takes at the start of a table row.
PARAMETER_SYMBOL_PATTERN = re.compile(
    r"^(?:[a-zA-Z]_\{?\d+\}?|[a-zA-Z]\d+|k(?:on|off|cat|m|\d+)?|v(?:max|\d+)?"
    r"|r_?\d*|beta|gamma|alpha|delta|lambda|mu|sigma|theta|rho"
    r"|[αβγδεζηθικλμνξοπρστυφχψω])$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ParameterTableResult:
    is_parameter_table: bool
    score: float
    caption_similarity: float
    header_similarity: float
    keyword_score: float
    numeric_density: float
    symbol_density: float
    negative_keyword_score: float


def clean_text(value: object) -> str:
    if value is None:
        return ""
    text = re.sub(r"<[^>]+>", " ", str(value))
    return re.sub(r"\s+", " ", text).strip().lower()


def tokenize(text: str) -> list[str]:
    text = clean_text(text)
    return re.findall(
        r"[a-zA-Z]+(?:_\d+|\d+)?|[αβγδεζηθικλμνξοπρστυφχψω]|\d+(?:\.\d+)?",
        text,
    )


def _term_frequency(tokens: Sequence[str]) -> Counter[str]:
    counts = Counter(tokens)
    total = sum(counts.values())
    if total == 0:
        return Counter()
    return Counter({token: count / total for token, count in counts.items()})


def cosine_similarity(text_a: str, text_b: str) -> float:
    """Cosine similarity between two strings using plain token frequencies
    (no scikit-learn needed - this doesn't need to be fancy)."""
    vector_a = _term_frequency(tokenize(text_a))
    vector_b = _term_frequency(tokenize(text_b))
    if not vector_a or not vector_b:
        return 0.0

    shared = set(vector_a) & set(vector_b)
    dot = sum(vector_a[t] * vector_b[t] for t in shared)
    mag_a = math.sqrt(sum(v * v for v in vector_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vector_b.values()))
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot / (mag_a * mag_b)


def maximum_similarity(text: str, reference_texts: Iterable[str]) -> float:
    """Return the strongest similarity found in the text.

    Long Marker sections may contain captions, cells, and footnotes.
    Comparing only the complete block can dilute an informative caption.
    Therefore, compare the complete text, individual lines, and short
    token windows against each reference phrase.
    """

    normalized = clean_text(text)

    if not normalized:
        return 0.0

    candidates = {normalized}

    # Compare individual lines or sentence-like fragments.
    for fragment in re.split(r"[\\n.;:]+", str(text)):
        cleaned = clean_text(fragment)
        if cleaned:
            candidates.add(cleaned)

    # Compare short word windows to detect informative phrases embedded
    # inside a longer table section.
    tokens = tokenize(normalized)

    for window_size in range(2, min(9, len(tokens) + 1)):
        for start in range(len(tokens) - window_size + 1):
            candidates.add(" ".join(tokens[start:start + window_size]))

    scores = [
        cosine_similarity(candidate, reference)
        for candidate in candidates
        for reference in reference_texts
    ]

    return max(scores, default=0.0)


def keyword_score(text: str) -> float:
    normalized = clean_text(text)
    if not normalized:
        return 0.0
    matches = sum(1 for kw in PARAMETER_KEYWORDS if kw in normalized)
    return min(matches / 5.0, 1.0)  # a few hits is enough to max this out


def negative_keyword_score(text: str) -> float:
    normalized = clean_text(text)
    if not normalized:
        return 0.0
    matches = sum(1 for kw in NEGATIVE_KEYWORDS if kw in normalized)
    return min(matches / 3.0, 1.0)


def looks_numeric(value: object) -> bool:
    text = clean_text(value)
    if not text or text in {"-", "—", "–", "na", "n/a", "none"}:
        return False

    patterns = [
        r"^[+-]?\d+(?:\.\d+)?$",
        r"^[+-]?\d+(?:\.\d+)?\s*[-–]\s*[+-]?\d+(?:\.\d+)?$",
        r"^[+-]?\d+(?:\.\d+)?\s*(?:±|\+/-)\s*\d+(?:\.\d+)?$",
        r"^[+-]?\d+(?:\.\d+)?(?:e[+-]?\d+)$",
        r"^\d+(?:\.\d+)?\s*%$",
    ]
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def numeric_density(rows: Sequence[Sequence[object]]) -> float:
    nonempty = 0
    numeric = 0
    for row in rows:
        for cell in row:
            if not clean_text(cell):
                continue
            nonempty += 1
            if looks_numeric(cell):
                numeric += 1
    return numeric / nonempty if nonempty else 0.0


def looks_like_parameter_symbol(value: object) -> bool:
    text = clean_text(value).replace(" ", "")
    if not text or len(text) > 15:
        return False
    return bool(PARAMETER_SYMBOL_PATTERN.match(text))


def symbol_density(rows: Sequence[Sequence[object]]) -> float:
    # only look at the first column - that's where symbols usually live
    first_cells = [row[0] for row in rows if row]
    if not first_cells:
        return 0.0
    hits = sum(1 for cell in first_cells if looks_like_parameter_symbol(cell))
    return hits / len(first_cells)


class ParameterTableClassifier:
    """Scores a table on how likely it is to be a parameter table, and
    flags it as one once the score clears `threshold`."""

    def __init__(self, threshold: float = 0.50) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be between 0 and 1")
        self.threshold = threshold

    def predict(
        self,
        caption: str,
        headers: Sequence[object],
        rows: Sequence[Sequence[object]],
    ) -> ParameterTableResult:
        header_text = " ".join(clean_text(h) for h in headers)
        combined_text = f"{clean_text(caption)} {header_text}".strip()

        caption_similarity = maximum_similarity(caption, PARAMETER_CAPTION_REFERENCES)
        header_similarity = maximum_similarity(header_text, PARAMETER_HEADER_REFERENCES)
        kw_score = keyword_score(combined_text)
        num_density = numeric_density(rows)
        sym_density = symbol_density(rows)
        neg_score = negative_keyword_score(combined_text)

        # weights are hand-picked, not tuned on data - caption/header wording
        # is the strongest signal, negative keywords just knock the score down
        raw_score = (
            0.30 * caption_similarity
            + 0.25 * header_similarity
            + 0.20 * kw_score
            + 0.15 * num_density
            + 0.10 * sym_density
            - 0.20 * neg_score
        )
        score = max(0.0, min(raw_score, 1.0))

        return ParameterTableResult(
            is_parameter_table=score >= self.threshold,
            score=round(score, 4),
            caption_similarity=round(caption_similarity, 4),
            header_similarity=round(header_similarity, 4),
            keyword_score=round(kw_score, 4),
            numeric_density=round(num_density, 4),
            symbol_density=round(sym_density, 4),
            negative_keyword_score=round(neg_score, 4),
        )
