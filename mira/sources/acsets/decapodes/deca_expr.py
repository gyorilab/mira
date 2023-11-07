from copy import copy

from mira.metamodel.decapodes import *
from mira.sources.acsets.decapodes.util import PARTIAL_TIME_DERIVATIVE

__all__ = ['preprocess_decaexpr']


def get_variables_mapping_decaexpr(decaexpr_json):
    # First loop through the context to get the variables
    # then loop through the equations to get the remaining variables
    if "model" in decaexpr_json:
        decaexpr_json = decaexpr_json["model"]

    yielded_variable_names = set()
    var_dict = {ix: Variable(variable_id=ix, type=_type, name=name, ) for
                ix, (name, _type) in enumerate(
            recursively_find_variables_decaexpr_json(decaexpr_json,
                                                     yielded_variable_names))}
    return var_dict


def recursively_find_variables_decaexpr_json(decaexpr_json, yielded_variables):
    """

    Parameters
    ----------
    decaexpr_json : dict | list
        The 'model' field of the decaexpr JSON
    yielded_variables : set
        The set of variables that have already been yielded

    Yields
    ------
    : tuple[str, str]
        A tuple of the variable type and name to be used to initialize the
        Variable class
    """
    assert isinstance(yielded_variables, set)

    # Yield variable type and name
    if isinstance(decaexpr_json, dict):
        if "_type" in decaexpr_json:
            # Under 'equation'
            if decaexpr_json["_type"] == "Var":
                name = decaexpr_json["name"]
                _type = "Form0"
                if name not in yielded_variables:
                    yield name, _type
                    yielded_variables.add(name)

            # Literal, under 'equation'
            elif decaexpr_json["_type"] == "Lit":
                name = decaexpr_json["name"]
                _type = "Literal"
                if name not in yielded_variables:
                    yield name, _type
                    yielded_variables.add(name)

            # Under 'context'
            elif decaexpr_json["_type"] == "Judgement":
                # type comes from the 'dim' field here
                name = decaexpr_json["var"]["name"]
                _type = decaexpr_json["dim"]
                if name not in yielded_variables:
                    yield name, _type
                    yielded_variables.add(name)

            # Top level
            elif decaexpr_json["_type"] == "DecaExpr":
                # Skip the header
                yield from recursively_find_variables_decaexpr_json(
                    decaexpr_json["context"], yielded_variables)
                yield from recursively_find_variables_decaexpr_json(
                    decaexpr_json["equations"], yielded_variables)

            # Equation object, under 'equations' yield from lhs and rhs
            elif decaexpr_json["_type"] == "Eq":
                yield from recursively_find_variables_decaexpr_json(
                    decaexpr_json["lhs"], yielded_variables)
                yield from recursively_find_variables_decaexpr_json(
                    decaexpr_json["rhs"], yielded_variables)

            # Derivative (tangent variable), under 'equations' -> 'lhs'/rhs'
            elif decaexpr_json["_type"] == "Tan":
                yield from recursively_find_variables_decaexpr_json(
                    decaexpr_json["var"], yielded_variables)

            # Multiplication, under 'equations' -> 'rhs'/lhs'
            elif decaexpr_json["_type"] == "Mult":
                # todo: probably need to handle other binary operations here
                for arg in decaexpr_json["args"]:
                    yield from recursively_find_variables_decaexpr_json(arg,
                                                                        yielded_variables)

            else:
                raise NotImplementedError(
                    f"Unhandled variable type: {decaexpr_json['_type']}")
        else:
            for value in decaexpr_json.values():
                yield from recursively_find_variables_decaexpr_json(value,
                                                                    yielded_variables)
    elif isinstance(decaexpr_json, list):
        for value in decaexpr_json:
            yield from recursively_find_variables_decaexpr_json(value,
                                                                yielded_variables)
    else:
        raise NotImplementedError(
            f"Unhandled type: {type(decaexpr_json)}: {decaexpr_json}")


def get_placeholder_mult(variable_indices, op2s_indexed):
    """Given a set of variable indices, find the top placeholder index

    Parameters
    ----------
    variable_indices : set[int]
        A set of variable indices to look for
    op2s_indexed : dict[int, Op2]
        A lookup of op2s by their index

    Returns
    -------
    int
        The index of the top placeholder variable, if any is found
    """
    # todo: DEBUG this function
    def _get_res(ix1: int, ix2: int):
        for op2 in op2s_indexed.values():
            if (op2.proj1 == ix1 and op2.proj2 == ix2 or
                    op2.proj1 == ix2 and op2.proj2 == ix1):
                return op2.res
        return None

    new_variable_indices = copy(variable_indices)

    # Look for the op2 that uses both variables. If found, remove both
    # variables from the list and add the result to the list
    new_indices = set()
    used_indices = set()
    for ix_1, ix_2 in zip(
            list(variable_indices)[:-1], list(variable_indices)[1:]
    ):
        res = _get_res(ix_1, ix_2)
        if res is not None:
            new_indices.add(res)
            used_indices.add(ix_1)
            used_indices.add(ix_2)

    # Remove the used indices
    new_variable_indices -= used_indices

    # Add the new indices
    new_variable_indices |= new_indices

    # If there is only one variable left, return it
    if len(new_variable_indices) == 1:
        return new_variable_indices.pop()
    else:
        # If the list is unchanged, there is no placeholder
        if new_variable_indices == variable_indices:
            return None
        else:
            # Otherwise, recurse - there are more placeholders to find
            return get_placeholder_mult(new_variable_indices, op2s_indexed)


def find_top_placeholder_variable_mult(decaexpr_equation_json, op2s_indexed,
                                       variable_name_to_index,
                                       variable_lookup):
    """Returns the top level variable in the equation"""
    # todo: handle other binary operations than Mult
    mult_args = decaexpr_equation_json["args"]
    args_indices = {variable_name_to_index[arg["name"]] for arg in mult_args}
    placeholder_ix = get_placeholder_mult(args_indices, op2s_indexed)
    return variable_lookup[placeholder_ix]


def find_unary_operations_json(decaexpr_equation_json, op2s_indexed,
                               variable_name_to_index, variable_lookup,
                               tangent_variables):
    """Returns an Op1 object if the equation is a unary operation, otherwise
    returns None"""
    rhs = decaexpr_equation_json["rhs"]
    lhs = decaexpr_equation_json["lhs"]

    # todo: handle other unary operations, currently assumes time derivative
    #  is the only unary operation
    if rhs["_type"] == "Tan":
        derivative_side = rhs
        result_side = lhs
    elif lhs["_type"] == "Tan":
        derivative_side = lhs
        result_side = rhs
    else:
        return None

    # Find the result side: if a single variable, use that, if it contains
    # multiple variables, find the placeholder variable among the op2s
    if result_side["_type"] == "Var":
        result_side_index = variable_name_to_index[result_side["name"]]
    elif result_side["_type"] == "Mult":
        # Find the top level variable: start from left and go right
        result_side_variable = find_top_placeholder_variable_mult(
            result_side, op2s_indexed, variable_name_to_index, variable_lookup
        )
        result_side_index = result_side_variable.variable_id
    else:
        # todo: handle other binary operations
        raise NotImplementedError(
            f"Unhandled result side type: {result_side['_type']}")

    derivative_arg_name = derivative_side["var"]["name"]

    # Create unary operation of the derivative side
    op1 = Op1(src=variable_name_to_index[derivative_arg_name],
              tgt=result_side_index, op1=PARTIAL_TIME_DERIVATIVE, )

    # Add tangent variable if it exists
    new_tangent_var_index = len(tangent_variables)
    tangent_variables[new_tangent_var_index] = TangentVariable(
        tangent_id=new_tangent_var_index, tangent_var_id=result_side_index,
        variable=variable_lookup[result_side_index], )

    return op1


def find_binary_operations_json(decaexpr_equation_json, variable_name_to_index,
                                variable_lookup):
    lhs = decaexpr_equation_json["lhs"]
    rhs = decaexpr_equation_json["rhs"]
    if lhs["_type"] != "Mult" and rhs["_type"] != "Mult":
        return []

    # Todo: handle other binary operations than Mult
    multipliation_side = lhs if lhs["_type"] == "Mult" else rhs

    # Loop factors in multiplication and add intermediate variables
    op2_list = []
    num_args = len(multipliation_side["args"])

    # For each pair of arguments, create a new variable then use that variable
    # in the next multiplication
    new_mult_result_variable_ix = None
    for ix in range(num_args-1):
        if ix == 0:
            # First iteration, create a new variable with the first two
            # arguments
            arg0 = multipliation_side["args"][ix]
            arg1 = multipliation_side["args"][ix + 1]
            arg0_name = arg0["name"]
            arg1_name = arg1["name"]
            arg0_index = variable_name_to_index[arg0_name]
            arg1_index = variable_name_to_index[arg1_name]
        else:
            # Subsequent iterations, use the result of the previous iteration
            assert new_mult_result_variable_ix is not None, \
                "Should not be None"  # fixme: for debugging, remove when/if
                                      #  this is working
            arg0_index = new_mult_result_variable_ix
            arg1 = multipliation_side["args"][ix + 1]
            arg1_name = arg1["name"]
            arg1_index = variable_name_to_index[arg1_name]

        # Create new result
        new_mult_result_variable_ix = len(variable_lookup)
        mult_ix = len([var_name for var_name in variable_name_to_index if
                       "mult" in var_name]) + 1
        mult_result_var = Variable(variable_id=new_mult_result_variable_ix,
                                   type="Form0", name=f"mult_{mult_ix}", )

        # Add new variable to lookup and index
        variable_lookup[new_mult_result_variable_ix] = mult_result_var
        variable_name_to_index[
            mult_result_var.name] = new_mult_result_variable_ix

        # Create new op2
        op2_list.append(Op2(proj1=arg0_index, proj2=arg1_index,
                            res=new_mult_result_variable_ix, op2="*",
                            # todo: handle other binary operations
                            ))

    return op2_list


def preprocess_decaexpr(decaexpr_json):
    # Note: the current code assumes that the decaexpr JSON includes the
    # header:
    # {
    #   "annotations": [],
    #   "header": {
    #     "description": "<description>",
    #     "name": "<name>",
    #     "_type": "Header",
    #     "model_version": "v1.0",
    #     "schema": "modelreps.io/DecaExpr",
    #     "schema_name": "DecaExpr"
    #   },
    #   "_type": "ASKEMDecaExpr",
    #   "model": { ... }
    # The model has the following structure:
    #   {
    #     "context": [
    #       {
    #         "dim": ...,  # 'Form0' - variable, 'Constant' - constant
    #         "var": {"name": "...", "_type": "..."}, _type = 'Var'
    #         "space": "...",  # 'Point' so far
    #         "_type": "..."  # 'Judgement' so far
    #       }, ...
    #     ]
    #     "_type": "DecaExpr",
    #     "equations": [
    #       {
    #         "lhs": { ... },
    #         "rhs": { ... },
    #         "_type": "Eq"
    #     ]
    #   }
    #
    # For equations, the lhs and rhs are can take on different forms:
    # - A time derivative of X (unary operation)
    #   "lhs": {"var": {"name": "X", "_type": "Var"},
    #           "_type": "Tan"},
    #   (V - velocity)
    #   "rhs": {"name": "V", "_type": "Var"}
    # - Multiplication (a binary operation):
    #   (-1) * (spring constant k) * (displacement X)
    #   "rhs": {"args": [{"name": "-1", "_type": "Lit"},
    #                    {"name": "k", "_type": "Var"}
    #                    {"name": "X", "_type": "Var"}],
    #           "_type": "Mult"},
    #  (time derivative of velocity)
    #   "lhs": {"var": {"name": "V", "_type": "Var"},
    #           "_type": "Tan"}

    # Collect variables, first just look at the context, then see if we need
    # to add any variables from the equations
    # Create Variables
    decaexpr_json_model = decaexpr_json["model"]
    variables = get_variables_mapping_decaexpr(decaexpr_json_model)
    name_to_variable_index = {v.name: k for k, v in variables.items()}

    # Unary operations include derivatives
    # todo: what else is a unary operation? Would spatial derivatives look
    #  different from time derivatives?
    # Binary operations
    op2s_indexed = {}
    for equation in decaexpr_json_model["equations"]:
        op2_list = find_binary_operations_json(equation,
                                               name_to_variable_index,
                                               variables)
        for op2 in op2_list:
            op2s_indexed[len(op2s_indexed)] = op2

    op1s_indexed = {}
    tangent_variables = {}
    for equation in decaexpr_json_model["equations"]:
        op1 = find_unary_operations_json(equation, op2s_indexed,
                                         name_to_variable_index, variables,
                                         tangent_variables)
        if op1 is not None:
            op1s_indexed[len(op1s_indexed)] = op1

    return Decapode(variables=variables, op1s=op1s_indexed, op2s=op2s_indexed,
                    summations={},  # Todo
                    tangent_variables=tangent_variables)
