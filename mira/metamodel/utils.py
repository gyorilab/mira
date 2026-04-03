__all__ = ['get_parseable_expression', 'revert_parseable_expression',
           'safe_parse_expr', 'sanity_check_tm']

import sympy
import re
import os
import unicodedata
from typing import Any, Optional
from functools import lru_cache

import requests


# Pre-compile the regular expression for performance
re_dots = re.compile(r'\.(?=\D)')
re_superscripts = re.compile(r"\^{(.*?)}")
re_curly_braces = re.compile(r'[{}]')


@lru_cache(maxsize=10000)
def get_parseable_expression(s: str) -> str:
    """Return an expression that can be parsed using sympy."""
    # Handle lambda which cannot be parsed by sympy
    s = s.replace('lambda', 'XXlambdaXX')
    # Handle dots which also cannot be parsed
    s = re_dots.sub('XX_XX', s)
    # Handle superscripts which are not allowed in sympy
    s = re_superscripts.sub(r"XXCXX{\1}", s)
    # Handle curly braces which are not allowed in sympy
    s = s.replace('{', 'XXCBO').replace('}', 'XXCBC')
    s = unicodedata.normalize('NFKC', s)
    return s


def revert_parseable_expression(s: str) -> str:
    """Return an expression to its original form."""
    s = s.replace('XXCXX', '^')
    s = s.replace('XXCBO', '{').replace('XXCBC', '}')
    s = s.replace('XX_XX', '.')
    s = s.replace('XXlambdaXX', 'lambda')
    return s


def safe_parse_expr(s: str, local_dict=None) -> sympy.Expr:
    """Parse an expression that may contain lambda functions."""
    return sympy.parse_expr(get_parseable_expression(s),
                            local_dict={get_parseable_expression(k): v
                                        for k, v in local_dict.items()}
                                        if local_dict else None,
                            evaluate=False)


def sanity_check_tm(tm):
    """Apply a short sanity check to a template model."""
    assert tm.templates
    all_concept_names = set(tm.get_concepts_name_map())
    all_parameter_names = set(tm.parameters)
    all_symbols = all_concept_names | all_parameter_names | ({tm.time.name} if tm.time else set())
    for template in tm.templates:
        assert template.rate_law
        symbols = template.rate_law.free_symbols
        for symbol in symbols:
            assert symbol.name in all_symbols, f"missing symbol: {symbol.name}"
    all_initial_names = {init.concept.name for init in tm.initials.values()}
    for concept in all_concept_names:
        assert concept in all_initial_names, f"missing initial condition for {concept}"


def is_ontological_child(child_curie: str, parent_curie: str,
                         api_url: Optional[str] = None):
    if api_url:
        base_url = api_url
    elif os.environ.get("MIRA_REST_URL"):
        base_url = os.environ.get("MIRA_REST_URL")
    else:
        try:
            import pystow
            base_url = pystow.get_config("mira", "rest_url")
        except ImportError:
            raise ValueError("api_url must be provided or MIRA_REST_URL must be set.")
    base_url = base_url.rstrip("/") + "/api" \
        if not base_url.endswith("/api") else base_url
    endpoint_url = base_url + '/is_ontological_child'

    res = requests.post(endpoint_url, json={"child_curie": child_curie,
                                            "parent_curie": parent_curie})

    res.raise_for_status()
    res_json = res.json()
    return res_json['is_child']
