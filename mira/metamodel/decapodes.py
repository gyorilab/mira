__all__ = ["Decapode", "Variable", "TangentVariable", "Summation",
           "Op1", "Op2"]

import copy
from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Mapping

import sympy


def expand_variable(variable, var_produced_map):
    if variable.expression:
        return variable.expression
    var_prod = var_produced_map.get(variable.id)
    if not var_prod:
        return sympy.Symbol(variable.name)
    elif isinstance(var_prod, Op1):
        return sympy.Function(var_prod.function_str)(expand_variable(
            var_prod.src, var_produced_map))
    elif isinstance(var_prod, Op2):
        arg1 = expand_variable(var_prod.proj1, var_produced_map)
        arg2 = expand_variable(var_prod.proj2, var_produced_map)
        if var_prod.function_str == '/':
            return arg1 / arg2
        elif var_prod.function_str == '*':
            return arg1 * arg2
        elif var_prod.function_str == '+':
            return arg1 + arg2
        elif var_prod.function_str == '-':
            return arg1 - arg2
        elif var_prod.function_str == '^':
            return arg1 ** arg2
        else:
            return sympy.Function(var_prod.function_str)(arg1, arg2)
    elif isinstance(var_prod, Summation):
        args = [expand_variable(summand, var_produced_map)
                for summand in var_prod.summands]
        return sympy.Add(*args)


class Decapode:
    def __init__(self, variables, op1s, op2s, summations, tangent_variables):
        self.variables = variables
        self.op1s = op1s
        self.op2s = op2s
        self.summations = summations
        self.tangent_variables = tangent_variables

        var_produced_map = {}
        root_variable_map = defaultdict(list)
        for ops, res_attr in ((self.op1s, 'tgt'), (self.op2s, 'res'),
                              (self.summations, 'sum')):
            for op_id, op in ops.items():
                produced_var = getattr(op, res_attr)
                if produced_var.id not in var_produced_map:
                    var_produced_map[produced_var.id] = op
                else:
                    one_op = var_produced_map.pop(produced_var.id)
                    root_variable_map[produced_var.id] = [one_op, op]

        new_vars = {}
        for var_id, var in copy.deepcopy(self.variables).items():
            if var_id not in root_variable_map:
                var.expression = expand_variable(var, var_produced_map)
                new_vars[var_id] = var
            else:
                var = RootVariable(var_id, var.type, var.name, var.identifiers)
                temp_var_map = copy.deepcopy(var_produced_map)
                temp_var_map[var_id] = root_variable_map[var_id][0]
                var.expression[0] = expand_variable(var.get_variable(),
                                                    temp_var_map)
                temp_var_map = copy.deepcopy(var_produced_map)
                temp_var_map[var_id] = root_variable_map[var_id][1]
                var.expression[1] = expand_variable(var.get_variable(),
                                                    temp_var_map)
                new_vars[var_id] = var
        self.update_vars(new_vars)

    def update_vars(self, variables):
        self.variables = variables
        for ops, var_args in ((self.op1s, ('src', 'tgt')),
                              (self.op2s, ('proj1', 'proj2', 'res')),
                              (self.summations, ('summands', 'sum')),
                              (self.tangent_variables, ('incl_var',))):
            for op in ops.values():
                for var_arg in var_args:
                    var_attr = getattr(op, var_arg)
                    if isinstance(var_attr, Variable):
                        setattr(op, var_arg, variables[var_attr.id])
                    elif isinstance(var_attr, list):
                        setattr(op, var_arg, [variables[var.id]
                                              for var in var_attr])


# TODO: Inherit from Concept?
@dataclass
class Variable:
    id: int
    type: str
    name: str
    expression: sympy.Expr = field(default=None)
    identifiers: Mapping[str, str] = field(default_factory=dict)


@dataclass
class RootVariable(Variable):
    expression: List[sympy.Expr] = field(default_factory=lambda: [None, None])

    def get_variable(self):
        return Variable(self.id, self.type, self.name,
                        self.identifiers)


@dataclass
class TangentVariable:
    id: int
    incl_var: Variable


@dataclass
class Summation:
    id: int
    summands: List[Variable]
    sum: Variable


@dataclass
class Op1:
    id: int
    src: Variable
    tgt: Variable
    function_str: str


@dataclass
class Op2:
    id: int
    proj1: Variable
    proj2: Variable
    res: Variable
    function_str: str
