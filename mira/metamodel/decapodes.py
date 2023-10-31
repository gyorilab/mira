import requests
import os
import sympy


class Decapode():
    def __init__(self, decapode_url):
        self.data = requests.get(decapode_url).json()

        # For testing purposes as original dynamics1 var contains unicode that cannot be parsed by sympy
        self.data['Var'][6]['name'] = 'dynamics1'

        self.variables = {var['_id']: Variable(variable_id=var['_id'], type=var['type'], name=var['name'],
                                               op1_list=self.data['Op1'], op2_list=self.data['Op2']) for var in
                          self.data['Var']}
        self.op1s = {op['_id']: Op1(src=self.variables[op['src']], tgt=self.variables[op['tgt']], op1=op['op1']) for
                     op in self.data['Op1']}
        self.op2s = {op['_id']: Op2(proj1=self.variables[op['proj1']], proj2=self.variables[op['proj2']],
                                    res=self.variables[op['res']],
                                    op2=op['op2']) for op in self.data['Op2']}

        self.summations = {summation['_id']: Summation(summation_id=summation['_id'],
                                                       summands=[Summand(summand_id=summand['_id'],
                                                                         summand_var_id=summand['summand'],
                                                                         summation_id=summand['summation'])
                                                                 for summand in self.data['Summand'] if
                                                                 summand['summation'] == summation['_id']],
                                                       result_var_id=summation['sum']) for summation in self.data['Σ']}

        self.tangent_variables = {tangent_var['_id']: TangentVariable(tangent_id=tangent_var['_id'],
                                                                      tangent_var_id=tangent_var['incl']) for
                                  tangent_var in self.data['TVar']}

        self.op1_list = self.data['Op1']
        self.op2_list = self.data['Op2']

        # These methods create a mapping between variable id to variable name if they are never a tgt/res for
        # a unary or binary operation respectively. Variable with id 7 can never be a result for a binary operation
        # but can be the result of a unary operation. Can try to refactor this such that we only use
        # 1 mapping for variables that are never outputs for both types of operations
        self.variable_expression_map_op1 = {input_var.variable_id: input_var.name for input_var in
                                            self.get_only_inputs_op1()}
        self.variable_expression_map_op2 = {input_var.variable_id: input_var.name for input_var in
                                            self.get_only_inputs_op2()}

        print()

    def get_only_outputs_op1(self):
        inputs = set()
        for op1 in self.op1s.values():
            inputs.add(op1.src)
        return set(self.variables.values()) - inputs

    def get_only_outputs_op2(self):
        inputs = set()
        for op2 in self.op2s.values():
            inputs.add(op2.proj1)
            inputs.add(op2.proj2)
        return set(self.variables.values()) - inputs

    # Want to see if src for an operation1 is a res for operation2
    def get_only_inputs_op1(self):
        outputs = set()
        for op1 in self.op1s.values():
            outputs.add(op1.tgt)
        return set(self.variables.values()) - outputs

    def get_only_inputs_op2(self):
        outputs = set()
        for op2 in self.op2s.values():
            outputs.add(op2.res)
        return set(self.variables.values()) - outputs

    def get_op1_targets(self):
        return {op.tgt: op_id for op_id, op in self.op1s.items()}

    def get_op2_targets(self):
        return {op.res: op_id for op_id, op in self.op2s.items()}


class Variable:
    def __init__(self, variable_id, type, name, op1_list=None, op2_list=None):

        self.variable_id = variable_id
        self.type = type
        self.name = name

        self.op1_list = op1_list
        self.op2_list = op2_list

        # find operations that have their result/target as the variable_id
        self.relevant_op_1 = [op1 for op1 in self.op1_list if op1['tgt'] == self.variable_id]
        self.relevant_op_2 = [op2 for op2 in self.op2_list if op2['res'] == self.variable_id]

        self.mapping1 = {}
        self.mapping2 = {}
        self.mapping1[self.variable_id] = []
        self.mapping2[self.variable_id] = []

        self.linked_list = LinkedList()
        self.expression = None

        if not self.relevant_op_1 and not self.relevant_op_2:
            return

        # a variable id cannot be the result of multiple operations in op1 or op2 list
        # go through all the ops that have their target as self.variable_id
        for operation1 in self.relevant_op_1:
            # find all operations for unary operations where the src is a tgt
            self.find_res1(self.variable_id, operation1['src'], self.relevant_op_1)

        for operation2 in self.relevant_op_2:
            # find all operations for binary operations where proj1 is a res and where proj2 is a res
            self.find_res2(self.variable_id, operation2['proj1'], self.relevant_op_2)
            self.find_res2(self.variable_id, operation2['proj2'], self.relevant_op_2)

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.__repr__()

    # recursive method for identifying unary operator sources
    def find_res1(self, parent_var, child_var, rel_op1_list):
        if parent_var not in self.mapping1:
            self.mapping1[parent_var] = []
        if child_var not in self.mapping1:
            self.mapping1[child_var] = []
        if not rel_op1_list:
            return
        for operator1 in rel_op1_list:
            if operator1 not in self.mapping1[parent_var]:
                self.mapping1[parent_var].append(operator1)
            unary_op_src = [op1 for op1 in self.op1_list if operator1['src'] == op1['tgt']]
            for unary_operator in unary_op_src:
                self.find_res1(unary_operator['tgt'], unary_operator['src'], unary_op_src)

    # recursion for finding binary operator sources
    def find_res2(self, parent_var, child_var, rel_op2_list):
        if parent_var not in self.mapping2:
            self.mapping2[parent_var] = []
        if child_var not in self.mapping2:
            self.mapping2[child_var] = []
        if not rel_op2_list:
            return

        # This list contains all operations where the parent_variable is the result of a binary operations
        for operator2 in rel_op2_list:
            if operator2 not in self.mapping2[parent_var]:
                self.mapping2[parent_var].append(operator2)

            # find all binary operations where proj1 and proj2 (children) are the result of binary operations
            src_proj1 = [op2 for op2 in self.op2_list if op2['res'] == operator2['proj1']]
            src_proj2 = [op2 for op2 in self.op2_list if op2['res'] == operator2['proj2']]
            for binary_operator_1 in src_proj1:
                self.find_res2(binary_operator_1['res'], binary_operator_1['proj1'], src_proj1)
                self.find_res2(binary_operator_1['res'], binary_operator_1['proj2'], src_proj1)
            for binary_operator_2 in src_proj2:
                self.find_res2(binary_operator_2['res'], binary_operator_2['proj1'], src_proj2)
                self.find_res2(binary_operator_2['res'], binary_operator_2['proj2'], src_proj2)

    def create_unary_linked_list(self):
        for var_id, operator_list in self.mapping1.items():
            for operator in operator_list:
                if operator['src'] in self.mapping1:
                    self.linked_list.insert_end(operator['src'], operator['op1'])

    def build_self_expression_op2(self, decapode):
        while self.variable_id not in decapode.variable_expression_map_op2:
            for mapping_var_id, operation in self.mapping2.items():
                if mapping_var_id in decapode.variable_expression_map_op2:
                    continue
                elif mapping_var_id not in decapode.variable_expression_map_op2:
                    # if both proj 1 and proj 2 are in the variable expression map
                    if (operation[0]['proj1'] in decapode.variable_expression_map_op2 and operation[0]['proj2'] in
                        decapode.variable_expression_map_op2):
                        proj1_expression = decapode.variable_expression_map_op2[operation[0]['proj1']]
                        proj2_expression = decapode.variable_expression_map_op2[operation[0]['proj2']]
                        decapode.variable_expression_map_op2[mapping_var_id] = '(' + proj1_expression + operation[0][
                            'op2'] + proj2_expression + ')'

        self.expression = sympy.sympify(decapode.variable_expression_map_op2[self.variable_id])

        # this part of the function will then test to see if any of the variables (base-level) present in the
        # expression for a variable built up from binary operations are then targets of unary operations
        for free_symbol in self.expression.free_symbols:
            if str(free_symbol) in [decapode.variables[operator['tgt']].name for operator in decapode.data['Op1']]:
                unary_variable_id = next(var.variable_id for var in decapode.variables.values()
                                         if var.name == str(free_symbol))
                self.build_helper_expression_op1(unary_variable_id, free_symbol, decapode)

    # This method helps break down variables that are present in an expression for a variable built up from
    # binary operations that are the result of a unary operation. For example, if variable with ID 7 is involved in
    # creating an expression for a variable built from binary operations but itself isn't the result of a binary
    # operation, then build_self_expression_op2 assumes that variable with ID 7 is a base-level (leaf node)
    # variable. However, it could be the case that the variable with id 7 is a result of a unary operation and
    # that will require to break down the variable with unary op'ns even further and that is what this method is for
    def build_helper_expression_op1(self, var_id, free_symbol, decapode):
        str_expression = str(self.expression)
        while var_id not in decapode.variable_expression_map_op1:
            for mapping_var_id, operation in decapode.variables[var_id].mapping1.items():
                if mapping_var_id in decapode.variable_expression_map_op1:
                    continue
                elif mapping_var_id not in decapode.variable_expression_map_op1:
                    if operation[0]['src'] in decapode.variable_expression_map_op1:
                        str_expression = str_expression.replace(str(free_symbol),
                                                                operation[0]['op1'] + '(' +
                                                                decapode.variable_expression_map_op1[
                                                                    operation[0]['src']] + ')')
                        decapode.variable_expression_map_op1[mapping_var_id] = str_expression

        self.expression = sympy.sympify(str_expression)
        print()


class TangentVariable:
    def __init__(self, tangent_id, tangent_var_id):
        self.tangent_id = tangent_id
        self.tangent_var_id = tangent_var_id


class Summation:
    def __init__(self, summation_id, summands, result_var_id):
        self.summation_id = summation_id
        self.summands = summands
        self.result_var_id = result_var_id


class Summand:
    def __init__(self, summand_id, summand_var_id, summation_id):
        self.summand_id = summand_id
        self.summand_var_id = summand_var_id
        self.summantion_id = summation_id


class Op1:
    def __init__(self, src, tgt, op1):
        self.src = src
        self.tgt = tgt
        self.op1 = op1

    def __repr__(self):
        return f'Op1({self.src}, {self.tgt}, {self.op1})'

    def __str__(self):
        return self.__repr__()


class Op2:
    def __init__(self, proj1, proj2, res, op2):
        self.proj1 = proj1
        self.proj2 = proj2
        self.res = res
        self.op2 = op2

    def __repr__(self):
        return f'Op2({self.proj1}, {self.proj2}, {self.res}, {self.op2})'

    def __str__(self):
        return self.__repr__()


class LinkedListNode:
    def __init__(self, var_id, operator):
        self.var_id = var_id
        self.operator = operator
        self.next = None


class LinkedList:
    def __init__(self):
        self.head = None

    def insert_end(self, var_id, operator):
        new_node = LinkedListNode(var_id, operator)
        if self.head is None:
            self.head = new_node
            return

        current_node = self.head
        while current_node.next:
            current_node = current_node.next

        current_node.next = new_node


def main():
    decapode = requests.get(
        "https://raw.githubusercontent.com/ciemss/Decapodes.jl/sa_climate_modeling/examples/climate/ice_dynamics.json").json()


if __name__ == "__main__":
    main()
