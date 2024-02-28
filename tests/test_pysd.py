import unittest

import sympy
from mira.metamodel import safe_parse_expr
from mira.sources.system_dynamics.pysd import with_lookup_to_piecewise


class TestPySDUtils(unittest.TestCase):
    """Test pysd utility functions."""

    def test_with_lookup_to_piecewise(self):
        data = "WITH LOOKUP(time,([(0,0)-(500,100)],(0,0),(1,2),(2,1),(3,0),(4,2),(5,1),(1000,0)))"
        val = with_lookup_to_piecewise(data)
        rv = safe_parse_expr(val)
        self.assertIsInstance(rv, sympy.Expr)
