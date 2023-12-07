__all__ = [
    "Decapode",
    "Variable",
    "TangentVariable",
    "Summation",
    "Op1",
    "Op2",
    "RootVariable",
]

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
        return sympy.Function(var_prod.function_str)(
            expand_variable(var_prod.src, var_produced_map)
        )
    elif isinstance(var_prod, Op2):
        arg1 = expand_variable(var_prod.proj1, var_produced_map)
        arg2 = expand_variable(var_prod.proj2, var_produced_map)
        if var_prod.function_str == "/":
            return arg1 / arg2
        elif var_prod.function_str == "*":
            return arg1 * arg2
        elif var_prod.function_str == "+":
            return arg1 + arg2
        elif var_prod.function_str == "-":
            return arg1 - arg2
        elif var_prod.function_str == "^":
            return arg1**arg2
        else:
            return sympy.Function(var_prod.function_str)(arg1, arg2)
    elif isinstance(var_prod, Summation):
        args = [
            expand_variable(summand, var_produced_map)
            for summand in var_prod.summands
        ]
        return sympy.Add(*args)


class Decapode:
    """
    MIRA's internal representation of a decapode compute graph or decaexpr
    JSON.
    """

    def __init__(self, variables, op1s, op2s, summations, tangent_variables):
        """
        Create a Decapode based off multiple mappings of different parts of
        a Decapode.

        Parameters
        ----------
        variables : Dict[int,Variable]
            Mapping of Variables.
        op1s : Dict[int,Op1]
            Mapping of Op1s (Operation 1s).
        op2s : Dict[int,Op2]
            Mapping of Op2s (Operation 2s).
        summations : Dict[int,Summation]
            Mapping of Summations.
        tangent_variables : Dict[int,TangentVariable]
            Mapping of TangentVariables.
        """
        self.variables = variables
        self.op1s = op1s
        self.op2s = op2s
        self.summations = summations
        self.tangent_variables = tangent_variables

        var_produced_map = {}
        root_variable_map = defaultdict(list)
        for ops, res_attr in (
            (self.op1s, "tgt"),
            (self.op2s, "res"),
            (self.summations, "sum"),
        ):
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
                var.expression[0] = expand_variable(
                    var.get_variable(), temp_var_map
                )
                temp_var_map = copy.deepcopy(var_produced_map)
                temp_var_map[var_id] = root_variable_map[var_id][1]
                var.expression[1] = expand_variable(
                    var.get_variable(), temp_var_map
                )
                new_vars[var_id] = var
        self.update_vars(new_vars)

    def update_vars(self, variables):
        self.variables = variables
        for ops, var_args in (
            (self.op1s, ("src", "tgt")),
            (self.op2s, ("proj1", "proj2", "res")),
            (self.summations, ("summands", "sum")),
            (self.tangent_variables, ("incl_var",)),
        ):
            for op in ops.values():
                for var_arg in var_args:
                    var_attr = getattr(op, var_arg)
                    if isinstance(var_attr, Variable):
                        setattr(op, var_arg, variables[var_attr.id])
                    elif isinstance(var_attr, list):
                        setattr(
                            op, var_arg, [variables[var.id] for var in var_attr]
                        )


# TODO: Inherit from Concept?
@dataclass
class Variable:
    """
    Dataclass that represents a variable in MIRA's internal representation of
    a Decapode.

    Attributes
    ----------
    id : int
        The id of the tangent variable
    type: str
        The type of the variable.
    name : str
        The name of the variable.
    expression : sympy.Expr
        The expression of the variable.
    identifiers : Mapping[str,str]
        The mapping of namespaces to identifiers associated with the Variable.
    """

    id: int
    type: str
    name: str
    expression: sympy.Expr = field(default=None)
    identifiers: Mapping[str, str] = field(default_factory=dict)


@dataclass
class RootVariable(Variable):
    """
    Dataclass that represents a variable that is the output of a unary (
    derivative) operation and the output of a series of unary and binary
    operations as well.

    Attributes
    ----------
    expression : list[sympy.Expr]
        A list containing both expressions  associated with a RootVariable:
        One expression built up from a unary operation (derivative) and one
        built up from a series of unary and binary operations.
    """

    expression: List[sympy.Expr] = field(default_factory=lambda: [None, None])

    def get_variable(self):
        return Variable(
            self.id, self.type, self.name, identifiers=self.identifiers
        )


@dataclass
class TangentVariable:
    """
    Dataclass that represents a tangent variable in MIRA's internal
    representation of a Decapode.

    Attributes
    ----------
    id : int
        The id of the tangent variable.
    incl_var : Variable
        The variable that is the result of a derivative operation associated
        with the tangent variable.
    """

    id: int
    incl_var: Variable


@dataclass
class Summation:
    """
    Dataclass that represents a summation in MIRA's internal representation
    of a decapode.

    Attributes
    ----------
    id : int
        The id of the summation.
    summands : list[Variable]
        A list of Variables that are a part of the summation.
    sum : Variable
        The Variable that is the result of the summation.
    """

    id: int
    summands: List[Variable]
    sum: Variable


@dataclass
class Op1:
    """
    Dataclass that represents unary operations in MIRA's internal
    representation of a decapode.

    Attributes
    ----------
    id : int
        The id of the operation.
    src : Variable
        The Variable that is the source of the operation.
    tgt : Variable
        The Variable that is the target of the operation.
    function_str : str
        The operator of the operation.
    """

    id: int
    src: Variable
    tgt: Variable
    function_str: str


@dataclass
class Op2:
    """
    Dataclass that represents binary operations in MIRA's internal
    representation of a decapode.

    Attributes
    ----------
        id : int
            The id of the operation.
        proj1 : Variable
            The Variable that is the first input to the operation.
        proj2 : Variable
            The Variable that is the second input to the operation.
        res : Variable
            The variable that is the result of the operation.
        function_str : str
            The operator of the operation.
    """

    id: int
    proj1: Variable
    proj2: Variable
    res: Variable
    function_str: str
