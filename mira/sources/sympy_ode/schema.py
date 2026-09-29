from typing import List, Literal, Optional, Type

from pydantic import BaseModel, Field

__all__ = [
    "TableSelection", "TableSelectionResponse", "KeyValue", "Uncertainty",
    "DistributionSpec", "ExtractedParameter", "ScenarioSpec",
    "ScenarioExtractionResponse", "strict_schema",
]

class TableSelection(BaseModel):
    table_id: str = Field(description="The table id exactly as given.")
    relevant: bool = Field(
        description="True if the table likely reports values of model INPUT "
                    "parameters, or values that differ between scenarios "
                    "(countries, interventions, variants, periods).")
    reason: str = Field(description="One short sentence justifying the call.")


class TableSelectionResponse(BaseModel):
    tables: List[TableSelection]


class KeyValue(BaseModel):
    key: str
    value: str


class Uncertainty(BaseModel):
    kind: Literal["confidence_interval", "credible_interval", "range",
                  "standard_deviation", "standard_error", "iqr", "other"] = \
        Field(description="'range' for any fitted, prior, plausible or "
                          "sampled range ('0.1-0.5', '[0.1, 0.5]'); "
                          "'standard_deviation' for 'mean ± SD' or "
                          "'mean (SD)'; the CI kinds for stated intervals.")
    low: Optional[float] = Field(description="Lower bound, or null.")
    high: Optional[float] = Field(description="Upper bound, or null.")
    spread: Optional[float] = Field(
        description="The SD/SE value when kind is standard_deviation or "
                    "standard_error (the mean goes in `value`), otherwise "
                    "null.")
    level: Optional[float] = Field(
        description="Coverage as a fraction, e.g. 0.95 for a 95% CI, or null.")


class DistributionSpec(BaseModel):
    family: Literal["normal", "uniform", "lognormal", "gamma", "beta",
                    "exponential", "poisson", "other"]
    parameters: List[KeyValue] = Field(
        description="Distribution parameters as written, e.g. "
                    "[{key: 'mean', value: '5.2'}, {key: 'sd', value: '1.1'}].")


class ExtractedParameter(BaseModel):
    table_id: str = Field(description="The table the value was read from.")
    row_label: str = Field(
        description="The row label (symbol or description) exactly as it "
                    "appears in the table, for provenance.")
    display_name: str = Field(
        description="The parameter's symbol as written in the table, with "
                    "Greek letters as Unicode characters and sub/superscripts "
                    "as _ and ^, e.g. 'β', 'γ_1', 'R_0', 'μ_h', 'Λ'. Convert "
                    "LaTeX (\\beta), MathML and spelled-out Greek ('beta') to "
                    "the Unicode letter. If the table gives no symbol, use "
                    "the row label.")
    name: str = Field(
        description="The display_name spelled out in ASCII as a valid "
                    "Python/sympy identifier: each Greek letter becomes its "
                    "name, e.g. 'β' -> 'beta', 'γ_1' -> 'gamma_1', "
                    "'μ_h' -> 'mu_h', 'Λ' -> 'Lambda', 'R_0' -> 'R_0'. "
                    "Derive it from the symbol, never from the description. "
                    "Use the same name for the same parameter in every "
                    "scenario.")
    model_parameter: Optional[str] = Field(
        description="If a list of model parameters was supplied, the name of "
                    "the model parameter this row corresponds to; null if "
                    "none matches or no list was supplied.")
    description: Optional[str] = Field(
        description="What the parameter means, in plain words, e.g. "
                    "'transmission rate from infectious to susceptible' or "
                    "'mean incubation period'. Take it from the table's "
                    "description/definition column when there is one, "
                    "otherwise from the row label, caption or footnotes. "
                    "Null only if the tables give no clue.")
    value: Optional[float] = Field(
        description="The point estimate (or mean), when the cell gives it as "
                    "a number. Write scientific notation such as "
                    "'2.1 x 10^-3' as 0.0021. Null when the value is written "
                    "as an expression, or the cell has no point estimate.")
    value_expression: Optional[str] = Field(
        description="If the value is written as an expression, e.g. "
                    "'1/(70*360)', '1/5.2' or 'R_0*gamma', that expression "
                    "exactly as written, in sympy syntax (* and **). Do not "
                    "evaluate, simplify or reorder it. Otherwise null.")
    units: Optional[str] = Field(
        description="Units as a sympy expression over unit names, e.g. "
                    "'1/day', 'day', 'person', '1/(day*person)', "
                    "'dimensionless'. Null if not stated or inferable from "
                    "the caption/footnotes.")
    uncertainty: Optional[Uncertainty]
    distribution: Optional[DistributionSpec] = Field(
        description="Only if the table states a distribution or prior "
                    "explicitly (e.g. 'Gamma(2, 3)', 'U(0.1, 0.5)').")
    estimation: Literal["fitted", "literature", "assumed", "fixed",
                        "derived", "unknown"]
    citation: Optional[str] = Field(
        description="Reference text for the value, e.g. '[12]' or "
                    "'Li et al. 2020', or null.")
    verbatim: str = Field(description="The exact value cell text.")


class ScenarioSpec(BaseModel):
    name: str = Field(
        description="Short snake_case scenario name, e.g. 'italy', "
                    "'lockdown', 'omicron', 'age_0_17'.")
    description: Optional[str] = Field(
        description="What distinguishes this scenario, in one sentence.")
    parameters: List[ExtractedParameter] = Field(
        description="Only the values specific to this scenario.")


class ScenarioExtractionResponse(BaseModel):
    shared_parameters: List[ExtractedParameter] = Field(
        description="Values that apply to every scenario (or all values, if "
                    "the paper has a single parameterization).")
    scenarios: List[ScenarioSpec] = Field(
        description="One entry per distinct parameterization. Empty if the "
                    "paper has a single parameterization.")


def strict_schema(model: Type[BaseModel]) -> dict:
    """Return an OpenAI strict-mode JSON schema for a pydantic model."""
    from openai.lib._pydantic import to_strict_json_schema
    return to_strict_json_schema(model)
