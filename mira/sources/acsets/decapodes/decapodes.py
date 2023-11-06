__all__ = ['process_decapode']

from mira.metamodel.decapodes import *


def process_decapode(decapode_json):
    data = decapode_json

    variables = {
        var['_id']: Variable(
            variable_id=var['_id'],
            type=var['type'],
            name=var['name']
        ) for var in data['Var']
    }
    op1s = {
        op['_id']: Op1(
            src=variables[op['src']],
            tgt=variables[op['tgt']],
            op1=op['op1']
        ) for op in data['Op1']
    }
    op2s = {
        op['_id']: Op2(
            proj1=variables[op['proj1']],
            proj2=variables[op['proj2']],
            res=variables[op['res']],
            op2=op['op2']
        ) for op in data['Op2']
    }

    summations = {
        summation['_id']: Summation(
            summation_id=summation['_id'],
            summands=[
                Summand(
                    summand_id=summand['_id'],
                    summand_var_id=summand['summand'],
                    summation_id=summand['summation'],
                    var=variables[summand['summand']]
                )
                for summand in data['Summand']
                if summand['summation'] == summation['_id']
            ],
            result_var_id=summation['sum']
        ) for summation in data['Σ']
    }

    tangent_variables = {
        tangent_var['_id']: TangentVariable(
            tangent_id=tangent_var['_id'],
            tangent_var_id=tangent_var['incl'],
            variable=tangent_var['incl']
        ) for tangent_var in data['TVar']
    }

    return Decapode(
        variables=variables,
        op1s=op1s,
        op2s=op2s,
        summations=summations,
        tangent_variables=tangent_variables
    )
