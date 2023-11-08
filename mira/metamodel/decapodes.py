__all__ = ["Decapode", "Variable", "TangentVariable", "Summation", "Summand",
           "Op1", "Op2"]

import copy
from collections import defaultdict
from typing import List

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
        args = [expand_variable(summand.summand, var_produced_map)
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
                var.expression[0] = expand_variable(var.get_variable(), temp_var_map)
                temp_var_map = copy.deepcopy(var_produced_map)
                temp_var_map[var_id] = root_variable_map[var_id][1]
                var.expression[1] = expand_variable(var.get_variable(), temp_var_map)
                new_vars[var_id] = var
        self.variables = new_vars


class Variable:
    def __init__(self, id, type=None, name=None, identifiers=None):
        self.id = id
        self.type = type
        self.name = name
        self.symbol = sympy.Symbol(name)
        self.expression = None
        self.identifiers = identifiers

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.__repr__()


class RootVariable(Variable):
    def __init__(self, id, type=None, name=None, identifiers=None):
        super().__init__(id, type, name, identifiers)
        self.id = id
        self.type = type
        self.name = name
        self.symbol = sympy.Symbol(name)
        self.expression = [None, None]
        self.identifiers = identifiers

    def get_variable(self):
        return Variable(self.id, self.type, self.name,
                        self.identifiers)

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.__repr__()


class TangentVariable:
    def __init__(self, id, incl_var_id):
        self.id = id
        self.incl_var_id = incl_var_id
        self.expression = None
        self.src_var_id = None


class Summand:
    def __init__(self, id, summand, summation_id):
        self.id = id
        self.summand = summand
        self.summation_id = summation_id


class Summation:
    def __init__(self, id, summands: List[Summand], sum: Variable):
        self.id = id
        self.summands = summands
        self.sum = sum


class Op1:
    def __init__(self, id, src: Variable, tgt: Variable, op1: str):
        self.id = id
        self.src = src
        self.tgt = tgt
        self.function_str = op1
        self.function_symbol = sympy.Function(op1)

    def __repr__(self):
        return f'Op1({self.src}, {self.tgt}, {self.function_str})'

    def __str__(self):
        return self.__repr__()


class Op2:
    def __init__(self, id, proj1: Variable, proj2: Variable, res: Variable,
                 op2: str):
        self.id = id
        self.proj1 = proj1
        self.proj2 = proj2
        self.res = res
        self.function_str = op2
        self.function_symbol = sympy.Function(op2)

    def __repr__(self):
        return (f'Op2({self.proj1}, {self.proj2}, {self.res}, '
                f'{self.function_str})')

    def __str__(self):
        return self.__repr__()
