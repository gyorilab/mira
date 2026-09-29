import logging
import re
from dataclasses import dataclass, field
from string import Template
from typing import List, Optional, Type, TypeVar

import sympy
from pydantic import BaseModel

from mira.metamodel import (Distribution, Parameter, Scenario, 
                            TemplateModel,Unit)
from mira.metamodel.units import UNIT_SYMBOLS
from mira.metamodel.utils import safe_parse_expr
from mira.openai_utility import OpenAIClient
from mira.sources.sympy_ode.constants import (
    JATS_TABLE_FORMAT, MODEL_CONTEXT_TEMPLATE, MODEL_SUMMARY_TEMPLATE,
    SCENARIO_EXTRACTION_PROMPT, TABLE_SELECTION_PROMPT)
from mira.sources.sympy_ode.schema import (
    ExtractedParameter, ScenarioExtractionResponse, 
    TableSelectionResponse, strict_schema)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

DEFAULT_SCENARIO = "default"


class StructuredOutputError(Exception):
    """The LLM response could not be parsed into the requested schema."""


@dataclass
class PaperTable:
    """One table from a paper, with its caption, header and footer as text."""
    table_id: str                                     
    caption: str = ""                                 
    header: List[str] = field(default_factory=list)  
    footer: str = ""                                
    content: str = ""                               
    has_table: bool = True                            


def run_structured(client: OpenAIClient, prompt: str, model: Type[T]) -> T:
    """Run a chat completion constrained to ``model``'s JSON schema."""
    choice = client.run_chat_completion(prompt, schema=strict_schema(model))
    if choice.finish_reason == "length":
        raise StructuredOutputError(
            "response truncated; raise the client's max_completion_tokens")
    if getattr(choice.message, "refusal", None):
        raise StructuredOutputError(f"model refused: {choice.message.refusal}")
    try:
        return model.model_validate_json(choice.message.content)
    except ValueError as e:
        raise StructuredOutputError(str(e)) from e


def _transition(template) -> str:
    """A template as 'S -> E (controlled by I, A), rate S*beta*(A*kappa + I)'."""
    ends = [getattr(template, end, None) for end in ("subject", "outcome")]
    text = " -> ".join(c.name if c is not None else "∅" for c in ends)
    controllers = getattr(template, "controllers", None) or [
        c for c in [getattr(template, "controller", None)] if c is not None]
    if controllers:
        text += f" (controlled by {', '.join(c.name for c in controllers)})"
    return f"{text}, rate {template.rate_law}"


def _model_context(template_model: Optional[TemplateModel],
                   template: Template = MODEL_CONTEXT_TEMPLATE) -> str:
    """List each model parameter with the transitions whose rate law uses it,
    so the LLM can match table rows by role rather than by spelling."""
    if template_model is None or not template_model.parameters:
        return ""
    uses = {name: [] for name in template_model.parameters}
    for t in template_model.templates:
        if t.rate_law is not None:
            for name in template_model.get_parameters_from_rate_law(t.rate_law):
                uses.get(name, []).append(_transition(t))

    blocks = []
    for name, p in template_model.parameters.items():
        label = ", ".join(filter(None, (p.display_name, p.description)))
        lines = [f"- {name}" + (f" ({label})" if label else "")]
        lines += [f"    in {t}" for t in uses[name]] or [
            "    not used in any rate law"]
        blocks.append("\n".join(lines))
    return template.substitute(parameters="\n".join(blocks))


def _table_summary(t: PaperTable) -> str:
    lines = [f"=== table_id: {t.table_id}", f"caption: {t.caption}"]
    lines += [f"header: {row}" for row in t.header]
    if t.footer:
        lines.append(f"footer: {t.footer}")
    return "\n".join(lines)


def select_relevant_tables(
    tables: List[PaperTable],
    client: OpenAIClient,
    template_model: Optional[TemplateModel] = None,
) -> List[PaperTable]:
    """Stage 1: return the tables whose caption, header and footer suggest
    they hold model input parameters. Tables without a body are skipped."""
    readable = [t for t in tables if t.has_table]
    if not readable:
        return []
    prompt = TABLE_SELECTION_PROMPT.substitute(
        model_context=_model_context(template_model, MODEL_SUMMARY_TEMPLATE),
        tables="\n\n".join(map(_table_summary, readable)),
    )
    verdicts = {s.table_id: s for s in
                run_structured(client, prompt, TableSelectionResponse).tables}
    # Can log verdict and reasoning for each table if needed

    return [t for t in readable
            if t.table_id in verdicts and verdicts[t.table_id].relevant]


def extract_scenarios(
    tables: List[PaperTable],
    client: OpenAIClient,
    template_model: Optional[TemplateModel] = None,
) -> ScenarioExtractionResponse:
    """Stage 2: extract values from all relevant tables in one call, so the
    LLM can see e.g. that Table 1's fixed rates hold for every country
    fitted in Table 2."""
    prompt = SCENARIO_EXTRACTION_PROMPT.substitute(
        table_format=JATS_TABLE_FORMAT,
        model_context=_model_context(template_model),
        tables="\n\n".join(t.content for t in tables),
    )
    return run_structured(client, prompt, ScenarioExtractionResponse)


def _identifier(name: str) -> str:
    name = re.sub(r"\W", "_", name.strip()).strip("_") or "param"
    return f"p_{name}" if name[0].isdigit() else name


def _parse(text: str, symbols: bool = True):
    """Unevaluated sympy expression for ``text``, e.g. '1/(70*360)', or None.

    With ``symbols``, every name is a plain Symbol, so 'gamma' or 'beta' in
    'beta/gamma' aren't read as sympy functions.
    """
    local_dict = ({n: sympy.Symbol(n) for n in re.findall(r"[A-Za-z_]\w*", text)}
                  if symbols else None)
    try:
        return safe_parse_expr(text.replace("^", "**"), local_dict=local_dict)
    except Exception:
        return None


def _number(text: str) -> Optional[float]:
    expr = _parse(text, symbols=False)
    try:
        return float(expr)
    except (TypeError, ValueError):
        return None


def parse_units(units: Optional[str]) -> Optional[Unit]:
    """Parse an LLM unit string like '1/day' into a MIRA Unit."""
    if not units:
        return None
    if units.strip().lower() in {"dimensionless", "unitless", "1", "none"}:
        return Unit(sympy.Integer(1))
    try:
        return Unit(safe_parse_expr(units, local_dict=UNIT_SYMBOLS))
    except Exception:
        logger.warning("Could not parse units %r", units)
        return None


# ProbOnto type and parameter names (as in mira.sources.sbml.processor), each
# with the aliases papers and LLMs commonly use for it.
_PROBONTO = {
    "normal": ("Normal1", {"mean": ["mean", "mu", "location"],
                           "stdev": ["stdev", "sd", "std", "sigma", "scale"]}),
    "uniform": ("Uniform1", {"minimum": ["minimum", "min", "low", "lower", "a"],
                             "maximum": ["maximum", "max", "high", "upper", "b"]}),
    "lognormal": ("LogNormal1", {"meanLog": ["meanlog", "mean", "mu"],
                                 "stdevLog": ["stdevlog", "sdlog", "sd",
                                              "sigma", "stdev"]}),
    "gamma": ("Gamma1", {"shape": ["shape", "k", "alpha"],
                         "scale": ["scale", "theta"]}),
    "beta": ("Beta1", {"alpha": ["alpha", "a", "shape1"],
                       "beta": ["beta", "b", "shape2"]}),
    "exponential": ("Exponential1", {"rate": ["rate", "lambda"]}),
    "poisson": ("Poisson1", {"rate": ["rate", "lambda", "mean"]}),
}
_INTERVAL_KINDS = {"range", "confidence_interval", "credible_interval"}
_SPREAD_KINDS = {"standard_deviation", "standard_error"}


def to_distribution(p: ExtractedParameter, value) -> Optional[Distribution]:
    """The parameter's MIRA Distribution, in order of priority:

    1. a distribution named in the table ('Gamma(2, 3)'), mapped to ProbOnto
       names by alias, else by position; a Gamma rate becomes its scale
    2. a range, confidence or credible interval -> Uniform1(low, high)
    3. a standard deviation or error around ``value`` -> Normal1
    Anything else (e.g. an IQR) gives None.
    """
    if spec := p.distribution:
        if spec.family not in _PROBONTO:
            return None
        probonto_type, wanted = _PROBONTO[spec.family]
        given = {kv.key.strip().lower(): _number(kv.value)
                 for kv in spec.parameters}
        if spec.family == "gamma" and "rate" in given and "scale" not in given:
            rate = given.pop("rate")
            given["scale"] = 1 / rate if rate else None
        positional = list(given.values())
        values = {}
        for i, (name, aliases) in enumerate(wanted.items()):
            v = next((given[a] for a in aliases if a in given), None)
            if v is None and len(positional) == len(wanted):
                v = positional[i]
            if v is None:
                logger.warning("Distribution %s is missing %s", spec, name)
                return None
            values[name] = v
        return Distribution(type=probonto_type, parameters=values)

    u = p.uncertainty
    if u and u.kind in _INTERVAL_KINDS and None not in (u.low, u.high):
        return Distribution(type="Uniform1",
                            parameters={"minimum": u.low, "maximum": u.high})
    if u and u.kind in _SPREAD_KINDS and None not in (u.spread, value):
        return Distribution(type="Normal1",
                            parameters={"mean": value, "stdev": u.spread})
    return None


def to_mira_parameter(p: ExtractedParameter) -> Parameter:
    """One extracted record as a MIRA Parameter, named after the mapped model
    parameter if any. An expression value ('1/(70*360)') stays unevaluated."""
    value = p.value
    if p.value_expression:
        value = _parse(p.value_expression)
        if value is None:
            logger.warning("Could not parse value expression %r",
                           p.value_expression)
            value = p.value_expression
    return Parameter(
        name=_identifier(p.model_parameter or p.name),
        value=value,
        distribution=to_distribution(p, value),
        display_name=p.display_name or p.row_label,
        description=p.description,
        units=parse_units(p.units),
    )


def to_mira_scenarios(response: ScenarioExtractionResponse) -> List[Scenario]:
    """One Scenario per parameterization: the shared values plus its own,
    which override shared ones of the same name."""
    def convert(params):
        return {q.name: q for q in map(to_mira_parameter, params)}

    shared = convert(response.shared_parameters)
    if not response.scenarios:
        return [Scenario(DEFAULT_SCENARIO,
                         description="The paper's single parameterization",
                         parameters=list(shared.values()))]
    return [Scenario(_identifier(s.name), description=s.description,
                     parameters=list({**shared,
                                      **convert(s.parameters)}.values()))
            for s in response.scenarios]


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def extract_scenarios_from_paper(
    pmid: str,
    client: OpenAIClient,
    tables: List[PaperTable],
    template_model: Optional[TemplateModel] = None,
) -> List[Scenario]:
    """Extract MIRA Scenarios from the tables of one paper.

    Parameters
    ----------
    pmid :
        The PubMed id of the paper, for logging.
    client :
        The OpenAI client. All relevant tables are extracted in one response,
        so give it a generous ``max_completion_tokens`` (e.g. 32k).
    tables :
        The paper's tables, e.g. from ``XmlExtractor.find_tables()``.
    template_model :
        If given, its parameters and rate laws are sent to the LLM so table
        rows are named after the model's parameters, which is what
        ``template_model.apply_scenario`` matches on.

    Returns
    -------
    :
        The scenarios, or an empty list if no table is relevant or the
        extraction fails.
    """
    relevant = select_relevant_tables(tables, client, template_model)
    logger.info("PMID %s: %d tables, %d relevant (%s)", pmid, len(tables),
                len(relevant), ", ".join(t.table_id for t in relevant))
    if not relevant:
        return []
    try:
        response = extract_scenarios(relevant, client, template_model)
    except StructuredOutputError as e:
        logger.warning("PMID %s: extraction failed: %s", pmid, e)
        return []
    logger.debug("PMID %s: stage 2 response:\n%s", pmid,
                 response.model_dump_json(indent=2))
    return to_mira_scenarios(response)
