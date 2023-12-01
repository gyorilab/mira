__all__ = ["process_decapode"]

from collections import defaultdict

from mira.metamodel.decapodes import *


def process_decapode(decapode_json):
    """Process a Decapode compute graph JSON into a Decapode object

    Parameters
    ----------
    decapode_json : dict
        The Decapode compute graph JSON of a model

    Returns
    -------
    :
        The corresponding MIRA Decapode object
    """
    data = decapode_json

    variables = {
        var["_id"]: Variable(id=var["_id"], type=var["type"], name=var["name"])
        for var in data["Var"]
    }
    op1s = {
        op["_id"]: Op1(
            id=op["_id"],
            src=variables[op["src"]],
            tgt=variables[op["tgt"]],
            function_str=op["op1"],
        )
        for op in data["Op1"]
    }
    op2s = {
        op["_id"]: Op2(
            id=op["_id"],
            proj1=variables[op["proj1"]],
            proj2=variables[op["proj2"]],
            res=variables[op["res"]],
            function_str=op["op2"],
        )
        for op in data["Op2"]
    }

    summands_by_summation = defaultdict(list)
    for summand_json in data["Summand"]:
        var = variables[summand_json["summand"]]
        summands_by_summation[summand_json["summation"]].append(var)

    summations = {
        summation["_id"]: Summation(
            id=summation["_id"],
            summands=summands_by_summation[summation["_id"]],
            sum=variables[summation["sum"]],
        )
        for summation in data["Σ"]
    }

    tangent_variables = {
        tangent_var["_id"]: TangentVariable(
            id=tangent_var["_id"], incl_var=variables[tangent_var["incl"]]
        )
        for tangent_var in data["TVar"]
    }

    return Decapode(
        variables=variables,
        op1s=op1s,
        op2s=op2s,
        summations=summations,
        tangent_variables=tangent_variables,
    )
