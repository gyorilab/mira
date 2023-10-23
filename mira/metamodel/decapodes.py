import requests
import os


class Decapode():

    def __init__(self, var_id, op1_list, op2_list, variables=None):
        self.variable_id = var_id

        self.op1_list = op1_list
        self.op2_list = op2_list
        self.nodes = {}

        # find operations that have their result/target as the variable_id
        self.relevant_op_1 = [op1 for op1 in self.op1_list if op1['tgt'] == self.variable_id]
        self.relevant_op_2 = [op2 for op2 in self.op2_list if op2['res'] == self.variable_id]

        self.mapping1 = {}
        self.mapping2 = {}

        self.mapping1[self.variable_id] = []
        self.mapping2[self.variable_id] = []
        self.stack = Stack()
        self.tree = ExpressionTree()
        self.linked_list = LinkedList()
        self.expression = ''

        if not self.relevant_op_1 and not self.relevant_op_2:
            return

        self.stack = Stack()
        self.tree = ExpressionTree()

        # a variable id cannot be the result of multiple operations in op1 or op2 list
        # go through all the ops that have their target as self.variable_id

        for operation1 in self.relevant_op_1:
            self.mapping1[self.variable_id].append(operation1)

            # find all operations for unary operations where the src is a tgt
            unary_op_src = [op1 for op1 in self.op1_list if operation1['src'] == op1['tgt']]
            for src_operation1 in unary_op_src:
                self.find_res1(self.variable_id, src_operation1['src'], self.relevant_op_1)

        for operation2 in self.relevant_op_2:
            self.mapping2[self.variable_id].append(operation2)
            self.find_res2(self.variable_id, operation2['proj1'], self.relevant_op_2)
            self.find_res2(self.variable_id, operation2['proj2'], self.relevant_op_2)

    # recursive method for identifying unary operator sources

    def find_res1(self, parent_var, child_var, rel_op1_list):
        if parent_var not in self.mapping1:
            self.mapping1[parent_var] = []
        if child_var not in self.mapping1:
            self.mapping1[child_var] = []
        if not rel_op1_list:
            return
        # rel_op1_list = [op1 for op1 in self.op1_list if op1['tgt'] == parent_var]
        for operator1 in rel_op1_list:
            self.mapping1[parent_var].append(operator1)
            unary_op_src = [op1 for op1 in self.op1_list if operator1['src'] == op1['tgt']]
            self.find_res1(child_var, operator1['src'], unary_op_src)

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


class ExpressionTree:
    def __init__(self):
        self.Tree = list()
        self.Fringe = list()
        self.Root = 0


class TreeNode:
    def __init__(self, var_id=None, proj1_id=None, proj2_id=None, operator=None, next=None):
        self.variable_id = var_id
        self.proj1_id = proj1_id
        self.proj2_id = proj2_id
        self.operator = operator
        self.next = next


class Stack:
    def __init__(self):
        self.head = None

    def push(self, node):
        if not self.head:
            self.head = node
        else:
            node.next = self.head
            self.head = node

    def pop(self):
        if self.head:
            popped = self.head
            self.head = self.head.next
            return popped
        else:
            raise Exception("Stack is empty")


def main():
    decapode = requests.get(
        "https://raw.githubusercontent.com/ciemss/Decapodes.jl/sa_climate_modeling/examples/climate/ice_dynamics.json").json()


if __name__ == "__main__":
    main()
