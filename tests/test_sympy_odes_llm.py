import os
import unittest

from mira.openai_utility import OpenAIClient
from mira.sources.sympy_ode.llm_util import execute_template_model_from_sympy_odes


@unittest.skipIf(
    os.environ.get("GITHUB_ACTIONS") is not None,
    reason="Meant to be run locally",
)
@unittest.skipIf(
    os.environ.get("OPENAI_API_KEY") is None,
    reason="Need OPENAI_API_KEY environment variable to run",
)
def test_concept_data():
    ode_str = """import sympy
# Define time variable
t = sympy.symbols("t")

# Define the time-dependent variables
S, E, I, R = sympy.symbols("S E I R", cls=sympy.Function)

# Define the parameters
b, g, r = sympy.symbols("b g r")

odes = [
    sympy.Eq(S(t).diff(t), - b * S(t) * I(t)),
    sympy.Eq(E(t).diff(t), b * S(t) * I(t) - r * E(t)),
    sympy.Eq(I(t).diff(t), r * E(t) - g * I(t)),
    sympy.Eq(R(t).diff(t), g * I(t))
]"""

    client = OpenAIClient()
    tm = execute_template_model_from_sympy_odes(
        ode_str, attempt_grounding=True, client=client
    )
    assert tm is not None
    for concept in tm.get_concepts_map().values():
        assert concept is not None
        from mira.metamodel import Concept

        assert isinstance(concept, Concept)
        assert concept.name is not None
        assert concept.identifiers is not None
        assert len(concept.identifiers) > 0
        assert concept.context is not None
        assert len(concept.context) > 0
