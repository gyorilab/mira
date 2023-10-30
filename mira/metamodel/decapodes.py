import requests
import os
import sympy


class Decapode():
    def __init__(self, decapode_url):
        self.data = requests.get(decapode_url).json()
        self.variables = {var['_id']: Variable(var_id=var['_id'], type=var['type'], name=var['name'],
                                               op1_list=self.data['Op1'], op2_list=self.data['Op2']) for var in
                          self.data['Var']}
        self.op1 = {op['_id']: Op1(src=self.variables[op['src']], tgt=self.variables[op['tgt']], op1=op['op1']) for
                    op
                    in self.data['Op1']}
        self.op2 = {op['_id']: Op2(proj1=self.variables[op['proj1']], proj2=self.variables[op['proj2']],
                                   res=self.variables[op['res']],
                                   op2=op['op2']) for op in self.data['Op2']}

        self.op1_list = self.data['Op1']
        self.op2_list = self.data['Op2']

        self.variable_expression_map_op2 = {input_var.variable_id: input_var.name for input_var in
                                            self.get_only_inputs_op2()}

        self.variable_expression_map_initial = {input_var.variable_id: input_var.name for input_var in
                                                self.variables.values()}

    def get_only_outputs_op1(self):
        inputs = set()
        for op1 in self.op1.values():
            inputs.add(op1.src)
        return set(self.variables.values()) - inputs

    def get_only_outputs_op2(self):
        inputs = set()
        for op2 in self.op2.values():
            inputs.add(op2.proj1)
            inputs.add(op2.proj2)
        return set(self.variables.values()) - inputs

    def get_only_inputs_op1(self):
        outputs = set()
        for op1 in self.op1.values():
            outputs.add(op1.tgt)
        return set(self.variables.values()) - outputs

    def get_only_inputs_op2(self):
        outputs = set()
        for op2 in self.op2.values():
            outputs.add(op2.res)
        return set(self.variables.values()) - outputs

    def get_op1_targets(self):
        return {op.tgt: op_id for op_id, op in self.op1.items()}

    def get_op2_targets(self):
        return {op.res: op_id for op_id, op in self.op2.items()}


class Variable():
    def __init__(self, var_id, type, name, op1_list=None, op2_list=None):

        self.variable_id = var_id
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
        self.expression = ''

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

    # def create_expression(self, var_id, var_map, parent_var=None, proj_1=None):
    #
    #     if not self.mapping2[var_id]:
    #         return
    #
    #     if not parent_var:
    #         self.expression += self.name + ' = (' + var_map[self.mapping2[var_id][0]['proj1']] + \
    #                            self.mapping2[var_id][0]['op2'] + var_map[self.mapping2[var_id][0]['proj2']] + ')|'
    #     elif parent_var and proj_1:
    #         self.expression += '(parent_var:' + var_map[self.mapping2[parent_var][0]['proj1']] + ' = ' + var_map[
    #             self.mapping2[var_id][0]['proj1']] + self.mapping2[var_id][0]['op2'] + var_map[
    #                                self.mapping2[var_id][0]['proj2']] + ' )|'
    #     elif parent_var and not proj_1:
    #         self.expression += '(parent_var:' + var_map[self.mapping2[parent_var][0]['proj2']] + ' = ' + var_map[
    #             self.mapping2[var_id][0]['proj1']] + self.mapping2[var_id][0]['op2'] + var_map[
    #                                self.mapping2[var_id][0]['proj2']] + ' )|'
    #
    #     self.create_expression(self.mapping2[var_id][0]['proj1'], var_map, var_id, True)
    #     self.create_expression(self.mapping2[var_id][0]['proj2'], var_map, var_id, False)

    def build_expression_iterative_op2(self, variable_expression_map):
        while self.variable_id not in variable_expression_map:
            for variable_id, operation in self.mapping2.items():
                if variable_id in variable_expression_map:
                    continue
                elif variable_id not in variable_expression_map:
                    # if both proj 1 and proj 2 are in the variable expression map
                    if operation[0]['proj1'] in variable_expression_map and operation[0][
                        'proj2'] in variable_expression_map:
                        proj1_expression = variable_expression_map[operation[0]['proj1']]
                        proj2_expression = variable_expression_map[operation[0]['proj2']]
                        variable_expression_map[variable_id] = '(' + proj1_expression + operation[0][
                            'op2'] + proj2_expression + ')'


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
