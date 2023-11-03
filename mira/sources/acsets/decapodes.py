__all__ = ['process_decapode']

from mira.metamodel.decapodes import *


def process_decapode(decapode_json):
    data = decapode_json

    variables = {var['_id']: Variable(variable_id=var['_id'], type=var['type'], name=var['name'],
                                      op1_list=data['Op1'], op2_list=data['Op2']) for var in data['Var']}
    op1s = {op['_id']: Op1(src=variables[op['src']], tgt=variables[op['tgt']], op1=op['op1']) for op in data['Op1']}
    op2s = {op['_id']: Op2(proj1=variables[op['proj1']], proj2=variables[op['proj2']], res=variables[op['res']],
                           op2=op['op2']) for op in data['Op2']}

    summations = {summation['_id']: Summation(summation_id=summation['_id'],
                                              summands=[Summand(summand_id=summand['_id'],
                                                                summand_var_id=summand['summand'],
                                                                summation_id=summand['summation'],
                                                                var=variables[summand['summand']])
                                                        for summand in data['Summand'] if
                                                        summand['summation'] == summation['_id']],
                                              result_var_id=summation['sum']) for summation in data['Σ']}

    tangent_variables = {
        tangent_var['_id']: TangentVariable(tangent_id=tangent_var['_id'], tangent_var_id=tangent_var['incl'],
                                            variable=tangent_var['incl']) for
        tangent_var in data['TVar']}

    return Decapode(variables=variables, op1s=op1s, op2s=op2s, summations=summations,
                    tangent_variables=tangent_variables)


def get_variables_mapping_decaexpr(decaexpr_json):
    # First loop through the context to get the variables
    # then loop through the equations to get the remaining variables
    if "model" in decaexpr_json:
        decaexpr_json = decaexpr_json["model"]

    yielded_variable_names = set()
    var_dict = {
        ix: Variable(
            variable_id=ix,
            type=_type,
            name=name,
        ) for ix, (name, _type) in enumerate(
            recursively_find_variables_decaexpr_json(decaexpr_json,
                                                     yielded_variable_names)
        )
    }
    return var_dict


def recursively_find_variables_decaexpr_json(
    decaexpr_json,
    yielded_variables
):
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
                    yield from recursively_find_variables_decaexpr_json(
                        arg, yielded_variables)

            else:
                raise NotImplementedError(
                    f"Unhandled variable type: {decaexpr_json['_type']}"
                )
        else:
            for value in decaexpr_json.values():
                yield from recursively_find_variables_decaexpr_json(
                    value, yielded_variables)
    elif isinstance(decaexpr_json, list):
        for value in decaexpr_json:
            yield from recursively_find_variables_decaexpr_json(
                value, yielded_variables)
    else:
        raise NotImplementedError(
            f"Unhandled type: {type(decaexpr_json)}: {decaexpr_json}"
        )


PARTIAL_TIME_DERIVATIVE = "∂ₜ"
BINARY_OPERATIONS = {"Mult"}  # todo: extend
FUNCTION_NAME_MAPPING = {"♯": 'Sharp',
                         '⋆₁': 'dot_subscript_1',
                         '∂ₜ': "d_subscript_t",
                         '⋆₀⁻¹': 'dot_subscript_o_superscript_-1'}
INVERSE_FUNCTION_NAME_MAPPING = {v: k for k, v in FUNCTION_NAME_MAPPING.items()}


def get_placeholder_mult(mult_args, op2s_indexed, variable_name_to_index):
    def _get_placeholder(arg1_ix, arg2_ix):
        for op2 in op2s_indexed.values():
            if op2.proj1 == arg1_ix and op2.proj2 == arg2_ix:
                return op2.res

    placeholder_ix = None
    for ix, (arg1, arg2) in enumerate(zip(mult_args[:-1], mult_args[1:])):
        arg1_index = variable_name_to_index[arg1["name"]]
        arg2_index = variable_name_to_index[arg2["name"]]
        if placeholder_ix == 0:
            # First iteration, find the placeholder result
            placeholder_ix = _get_placeholder(arg1_index, arg2_index)
            if placeholder_ix is None:
                raise ValueError(
                    f"Could not find placeholder result for {arg1} * {arg2}"
                )
        else:
            # Subsequent iterations, use previous placeholder_ix and arg2
            placeholder_ix = _get_placeholder(placeholder_ix, arg2_index)
            if placeholder_ix is None:
                raise ValueError(
                    f"Could not find placeholder result for {arg1} * {arg2}"
                )
    return placeholder_ix


def find_top_level_placeholder_variable_name(decaexpr_equation_json,
                                             op2s_indexed,
                                             variable_name_to_index,
                                             variable_lookup):
    """Returns the name of the top level variable in the equation"""
    # todo: handle other binary operations than Mult
    mult_args = decaexpr_equation_json["args"]
    placeholder_ix = get_placeholder_mult(
        mult_args, op2s_indexed, variable_name_to_index
    )
    return variable_lookup[placeholder_ix].name


def find_unary_operations_json(decaexpr_equation_json,
                               op2s_indexed,
                               variable_name_to_index,
                               variable_lookup,
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

    # Find the result side: if a single variable, use that, if it's a combined
    # variable, find the top level variable
    if result_side["_type"] == "Var":
        result_side_index = variable_name_to_index[result_side["name"]]
    elif result_side["_type"] == "Mult":  # todo: handle other binary operations
        # Find the top level variable: start from left and go right
        result_side_variable = find_top_level_placeholder_variable_name(
            result_side, op2s_indexed, variable_name_to_index, variable_lookup
        )
        result_side_index = result_side_variable.variable_id
    else:
        raise NotImplementedError(
            f"Unhandled result side type: {result_side['_type']}"
        )

    derivative_arg_name = derivative_side["var"]["name"]

    # Create unary operation of the derivative side
    op1 = Op1(
        src=variable_name_to_index[derivative_arg_name],
        tgt=result_side_index,
        op1=PARTIAL_TIME_DERIVATIVE,
    )

    # Add tangent variable if it exists
    new_tangent_var_index = len(tangent_variables)
    tangent_variables[new_tangent_var_index] = TangentVariable(
        tangent_id=new_tangent_var_index,
        tangent_var_id=result_side_index,
        variable=variable_lookup[result_side_index],
    )

    return op1


def find_binary_operations_json(decaexpr_equation_json,
                                variable_name_to_index,
                                variable_lookup):
    lhs = decaexpr_equation_json["lhs"]
    rhs = decaexpr_equation_json["rhs"]
    if lhs["_type"] != "Mult" and rhs["_type"] != "Mult":
        return []

    # Todo: handle other binary operations than Mult
    multipliation_side = lhs if lhs["_type"] == "Mult" else rhs

    # Loop factors in multiplication and add intermediate variables
    op2_list = []
    for arg0, arg1 in zip(
            multipliation_side["args"][:-1], multipliation_side["args"][1:]
    ):
        arg0_name = arg0["name"]
        arg1_name = arg1["name"]
        # todo: handle missing name?
        arg0_index = variable_name_to_index[arg0_name]
        arg1_index = variable_name_to_index[arg1_name]

        # Create new result
        new_mult_result_variable_ix = len(variable_lookup)
        mult_ix = len([var_name for var_name in variable_name_to_index if
                       "mult" in var_name]) + 1
        mult_result_var = Variable(
            variable_id=new_mult_result_variable_ix,
            type="Form0",
            name=f"mult_{mult_ix}",
        )

        # Add new variable to lookup
        variable_lookup[new_mult_result_variable_ix] = mult_result_var

        # Create new op2
        op2_list.append(
            Op2(
                proj1=arg0_index,
                proj2=arg1_index,
                res=new_mult_result_variable_ix,
                op2="*",  # todo: handle other binary operations
            )
        )

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
        op2_list = find_binary_operations_json(
            equation, name_to_variable_index, variables
        )
        for op2 in op2_list:
            op2s_indexed[len(op2s_indexed)] = op2

    op1s_indexed = {}
    tangent_variables = {}
    for equation in decaexpr_json_model["equations"]:
        op1 = find_unary_operations_json(
            equation, op2s_indexed, name_to_variable_index, variables, tangent_variables
        )
        if op1 is not None:
            op1s_indexed[len(op1s_indexed)] = op1

    return Decapode(
        variables=variables,
        op1s=op1s_indexed,
        op2s=op2s_indexed,
        summations={},  # Todo
        tangent_variables=tangent_variables,
    )
