import requests
import os

test = None


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

        self.tree = ExpressionTree()
        self.linked_list = LinkedList()

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

    def insert_all(self, var_id, operator):
        if not self.mapping2[var_id]:
            return

        self.tree.insert(operator[0]['op2'])
        self.tree.insert(operator[0]['proj1'])
        self.tree.insert(operator[0]['proj2'])

        self.insert_all(operator[0]['proj1'], self.mapping2[operator[0]['proj1']])
        self.insert_all(operator[0]['proj2'], self.mapping2[operator[0]['proj2']])


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


def is_operator(s):
    s = str(s)
    if '+' in s:
        return True
    if '-' in s:
        return True
    if '*' in s:
        return True
    if '/' in s:
        return True
    if '^' in s:
        return True
    return False


class ExpressionTree:
    def __init__(self):
        self.Tree = []
        for index in range(1, 30):
            self.Tree.append(TreeNode(left_child_index=index))
        self.fringe = []
        self.root = 0
        self.next_free_child = 0

    def insert(self, new_token):
        if self.next_free_child == -1:  # check if tree is full
            return "Tree Full"
            # tree is not full, safe to insert new token
        if self.next_free_child == 0:
            self.Tree[self.root].variable_id = new_token
            self.next_free_child = self.Tree[self.root].left_child
            self.Tree[self.root].left_child = -1
        else:
            # insert into tree with existing nodes
            # starting with Root
            current = 0  # index of the current node
            previous = -1  # index of previous node
            new_node = self.Tree[self.next_free_child]  # declare new node
            new_node.variable_id = new_token
            # Finding the node at which the NewNode can be inserted
            while current != -1:
                curr_node = self.Tree[current]
                # check if CurrNode contains an operator
                if is_operator(curr_node.variable_id):
                    # if LeftChild is empty, insert here
                    if curr_node.left_child == -1:
                        curr_node.left_child = self.next_free_child
                        self.next_free_child = new_node.left_child
                        new_node.left_child = -1
                        current = -1
                    # if RightChild is empty, insert here
                    elif curr_node.right_child == -1:
                        curr_node.right_child = self.next_free_child
                        self.next_free_child = new_node.left_child
                        new_node.left_child = -1
                        current = -1
                    # if LeftChild is an operator
                    # traverse LeftChild subtree
                    elif is_operator(self.Tree[curr_node.left_child].variable_id):
                        previous = current
                        current = curr_node.left_child
                        self.fringe.append(previous)
                    # if RightChild is an operator
                    # traverse RightChild subtree
                    elif is_operator(self.Tree[curr_node.right_child].variable_id):
                        previous = current
                        current = curr_node.right_child
                        self.fringe.append(previous)
                    # traverse right subtree
                    else:
                        previous = self.fringe.pop(-1)
                        current = self.Tree[previous].right_child
                # no place to insert
                else:
                    return "Cannot be inserted"

    def display(self):
        for index in range(len(self.Tree)):
            print("Index: ", index, "| Variable ID: ", self.Tree[index].variable_id)

    def infix(self, root, arr):
        if root.variable_id is not None:
            if is_operator(root.variable_id):
                arr.append('(')
            self.infix(self.Tree[root.left_child], arr)
            arr.append(root.DataValue)
            self.infix(self.Tree[root.right_child], arr)
            if is_operator(root.variable_id):
                arr.append(')')


class TreeNode:
    def __init__(self, left_child_index, variable_id=None):
        self.variable_id = None
        self.left_child = left_child_index
        self.right_child = -1


def main():
    decapode = requests.get(
        "https://raw.githubusercontent.com/ciemss/Decapodes.jl/sa_climate_modeling/examples/climate/ice_dynamics.json").json()


if __name__ == "__main__":
    main()
