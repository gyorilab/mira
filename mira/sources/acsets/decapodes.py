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


def find_binary_operations_json(decaexpr_equation_json,
                                variable_name_to_index,
                                variable_lookup):
    lhs = decaexpr_equation_json["lhs"]
    rhs = decaexpr_equation_json["rhs"]
    if "Mult" not in lhs and "Mult" not in rhs:
        return []

    # Todo: handle other binary operations than Mult
    multipliation_side = lhs if "Mult" in lhs else rhs

    # Loop factors in multiplication and add intermediate variables
    op2_list = []
    for ix, (arg0, arg1) in enumerate(zip(
            multipliation_side["args"][:-1], multipliation_side["args"][1:]
    )):
        arg0_name = arg0["name"]
        arg1_name = arg1["name"]
        # todo: handle missing name?
        arg0_index = variable_name_to_index[arg0_name]
        arg1_index = variable_name_to_index[arg1_name]

        # Create new result
        new_mult_result_variable_ix = len(variable_lookup)
        mult_ix = max(
            len([var_name for var_name in variable_name_to_index
                 if "mult" in var_name]),
            0
        ) + 1
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
    variables = get_variables_mapping_decaexpr(decaexpr_json)
    name_to_variable_index = {v.name: k for k, v in variables.items()}

    # Unary operations include derivatives
    # todo: what else is a unary operation? Would spatial derivatives look
    #  different from time derivatives?
    op1s_indexed = {}
    op2s_indexed = {}

    # Binary operations
    for equation in decaexpr_json["equations"]:
        op2_list = find_binary_operations_json(
            equation, name_to_variable_index, variables
        )
        for op2 in op2_list:
            op2s_indexed[len(op2s_indexed)] = op2

    return Decapode(
        variables=variables,
        op1s=op1s_indexed,  # Todo
        op2s=op2s_indexed,
        summations={},  # Todo
        tangent_variables={},  # Todo
    )
