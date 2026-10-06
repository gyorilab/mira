__all__ = ["OdeChange", "record_change", "describe_changes"]

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OdeChange:
    """A single correction applied while building a TemplateModel.

    Attributes
    ----------
    kind :
        Machine-readable category, e.g. ``'time_varying_param_demoted'``.
    symbols :
        The symbol names the change concerns. Together with ``kind`` this
        identifies the change, so the same correction is only reported once.
    message :
        Description of what MIRA changed in the ODE code snippet to 
        produce a valid TemplateModel.
    instruction :
        Instructions for the LLM about how to change ODE code snippet 
        for the snippet to match what MIRA actually built.
    """

    kind: str
    symbols: Tuple[str, ...] = ()
    message: str = ""
    instruction: str = ""

    @property
    def key(self) -> Tuple:
        return self.kind, self.symbols


def record_change(changes: Optional[List[OdeChange]],
                  change: OdeChange) -> None:
    """Append a change to ``changes``, de-duplicating on ``key``."""
    if changes is None:
        return
    if any(existing.key == change.key for existing in changes):
        return
    changes.append(change)


def describe_changes(changes: List[OdeChange]) -> str:
    """Render changes as a numbered list of required edits, for a prompt."""
    lines = []
    for idx, change in enumerate(changes, start=1):
        lines.append("%d. %s\n   Required edit: %s"
                     % (idx, change.message, change.instruction))
    return "\n".join(lines)


def time_varying_param_change(func, time_variable) -> OdeChange:
    """Build the change record for a demoted time-varying parameter."""
    name = func.name
    return OdeChange(
        kind="time_varying_param_demoted",
        symbols=(name,),
        message=(
            "%s is used as a time-varying quantity but no definition for it "
            "was provided, so it was interpreted as a constant parameter %s."
            % (func, name)
        ),
        instruction=(
            "Declare `{name}` as a plain sympy Symbol instead of an undefined "
            "Function, and replace every application of it (`{name}({time})` "
            "and any other argument it is applied to) with the bare symbol "
            "`{name}`. Do not otherwise change the equations."
            .format(name=name, time=time_variable)
        ),
    )