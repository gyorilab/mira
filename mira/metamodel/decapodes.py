__all__ = ["Decapode", "Variable", "TangentVariable", "Summation", "Summand", "Op1", "Op2"]

import sympy


class Decapode:
    def __init__(self,
                 variables,
                 op1s,
                 op2s,
                 summations,
                 tangent_variables):

        self.variables = variables
        self.op1s = op1s
        self.op2s = op2s
        self.summations = summations
        self.tangent_variables = tangent_variables

        # These lines create a mapping between variable id to variable symbol/sympy.expr if they are never a tgt/res for
        # a unary or binary operation respectively. Variable with id 7 is not a result for a binary operation
        # but is the target of a unary operation.
        self.variable_expression_map_op1 = {input_var.variable_id: input_var.symbol for input_var in
                                            self.get_only_inputs_op1()}
        self.variable_expression_map_op2 = {input_var.variable_id: input_var.symbol for input_var in
                                            self.get_only_inputs_op2()}
        self.variable_expression_map_both_op = {input_var.variable_id: input_var.symbol for input_var in
                                                self.get_only_inputs_both()}

        # Define set of symbols that are never an output for both types of operation (i.e. base-level symbols)
        self.set_base_symbols = {var_name for var_name in self.variable_expression_map_both_op.values()}

        # Create a mapping of variables to unary/binary operations that result in the previously mentioned variables
        self.variable_relevant_operation_mapping = {}

        # Mapping a chain of unary operations that resembles a linked list data structure for each variable
        self.variable_op1_map_linkedlist = {}
        # Mapping a chain of binary operations that resembles a linked list data structure for each variable
        self.variable_op2_map_tree = {}

        for var_mapping_id, var in variables.items():
            self.variable_relevant_operation_mapping[var_mapping_id] = {}
            self.variable_relevant_operation_mapping[var_mapping_id]['unary'] = [op1 for op1 in self.op1s.values() if
                                                                                 op1.tgt.variable_id == var_mapping_id]
            self.variable_relevant_operation_mapping[var_mapping_id]['binary'] = [op2 for op2 in self.op2s.values() if
                                                                                  op2.res.variable_id == var_mapping_id]

            self.variable_op1_map_linkedlist[var_mapping_id] = {}
            self.variable_op2_map_tree[var_mapping_id] = {}

            for operation1 in self.variable_relevant_operation_mapping[var_mapping_id]['unary']:
                # find all operations for unary operations where the src is a tgt
                self.find_srcs_for_op1(var_mapping_id, var_mapping_id, operation1.src.variable_id,
                                       self.variable_relevant_operation_mapping[var_mapping_id]['unary'])

            for operation2 in self.variable_relevant_operation_mapping[var_mapping_id]['binary']:
                # find all operations for binary operations where proj1 is a res and where proj2 is a res
                self.find_srcs_for_op2(var_mapping_id, var_mapping_id, operation2.proj1.variable_id,
                                       self.variable_relevant_operation_mapping[var_mapping_id]['binary'])
                self.find_srcs_for_op2(var_mapping_id, var_mapping_id, operation2.proj2.variable_id,
                                       self.variable_relevant_operation_mapping[var_mapping_id]['binary'])

    # Recursively find all sources for a chain of unary operations where the first operation
    # results in variable with id = root_var_id
    def find_srcs_for_op1(self, root_var_id, parent_var_id, child_var_id, relevant_op_unary_list):
        """
            Parameters
            ----------
            root_var_id : int
                The id of the root variable for which this method is called initially on
            parent_var_id : int
                The id of the variable that is the result of a unary operation and for which we need to identify its
                source
            child_var_id: int
                The id of the variable that is the source of unary operation that leads to the parent variable
            relevant_op_unary_list: list
                A list of unary operations that results in the parent variable
            """

        # Identify derivative operation and if present, add it to its respective tangent variable expression field
        derivative_operation = next((op1 for op1 in relevant_op_unary_list if op1.op1 == '∂ₜ'), None)
        if derivative_operation is not None:
            tangent_var = next((tangent_var for tangent_var in self.tangent_variables.values() if
                                tangent_var.incl_var_id == derivative_operation.tgt.variable_id), None)
            tangent_var.src_var_id = derivative_operation.src.variable_id
            sympy_derivative_function = sympy.Function('∂ₜ')
            self.tangent_variables[tangent_var.tangent_id].expression = sympy_derivative_function(
                derivative_operation.src.symbol)

        if parent_var_id not in self.variable_op1_map_linkedlist[root_var_id]:
            self.variable_op1_map_linkedlist[root_var_id][parent_var_id] = []
        if child_var_id not in self.variable_op1_map_linkedlist[root_var_id]:
            self.variable_op1_map_linkedlist[root_var_id][child_var_id] = []
        if not relevant_op_unary_list:
            return
        for operator1 in relevant_op_unary_list:
            if operator1 not in self.variable_op1_map_linkedlist[root_var_id][parent_var_id]:
                self.variable_op1_map_linkedlist[root_var_id][parent_var_id].append(operator1)
            unary_op_src = [op1 for op1 in self.op1s.values() if operator1.src.name == op1.tgt.name]
            for unary_operator in unary_op_src:
                self.find_srcs_for_op1(root_var_id, unary_operator.tgt.variable_id, unary_operator.src.variable_id,
                                       unary_op_src)

    # Recursively find all sources for a chain of binary operations where the first operation
    # results in variable with id = root_var_id
    def find_srcs_for_op2(self, root_var_id, parent_var_id, child_var_id, relevant_op_binary_list):
        """
            Parameters
            ----------
            root_var_id : int
                The id of the root variable for which this method is called initially on
            parent_var_id : int
                The id of the variable that is the result of a binary operation and for which we need to identify its
                sources
            child_var_id: int
                The id of the variable that is one of the sources of binary operation that leads to the parent variable
            relevant_op_binary_list: list
                A list of binary variable that results in the parent variable
            """
        if parent_var_id not in self.variable_op2_map_tree[root_var_id]:
            self.variable_op2_map_tree[root_var_id][parent_var_id] = []
        if child_var_id not in self.variable_op2_map_tree[root_var_id]:
            self.variable_op2_map_tree[root_var_id][child_var_id] = []
        if not relevant_op_binary_list:
            return
        # This list contains all operations where the parent_variable is the result of a binary operations
        for operator2 in relevant_op_binary_list:
            if operator2 not in self.variable_op2_map_tree[root_var_id][parent_var_id]:
                self.variable_op2_map_tree[root_var_id][parent_var_id].append(operator2)

            # find all binary operations where proj1 and proj2 (children) are the result of binary operations
            src_proj1 = [op2 for op2 in self.op2s.values() if op2.res.variable_id == operator2.proj1.variable_id]
            src_proj2 = [op2 for op2 in self.op2s.values() if op2.res.variable_id == operator2.proj2.variable_id]

            for binary_operator_1 in src_proj1:
                self.find_srcs_for_op2(root_var_id, binary_operator_1.res.variable_id,
                                       binary_operator_1.proj1.variable_id, src_proj1)
                self.find_srcs_for_op2(root_var_id, binary_operator_1.res.variable_id,
                                       binary_operator_1.proj2.variable_id, src_proj1)
            for binary_operator_2 in src_proj2:
                self.find_srcs_for_op2(root_var_id, binary_operator_2.res.variable_id,
                                       binary_operator_2.proj1.variable_id, src_proj2)
                self.find_srcs_for_op2(root_var_id, binary_operator_2.res.variable_id,
                                       binary_operator_2.proj2.variable_id, src_proj2)

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

    def get_only_outputs_both(self):
        inputs = set()
        for op1 in self.op1s.values():
            inputs.add(op1.src)
        for op2 in self.op2s.values():
            inputs.add(op2.proj1)
            inputs.add(op2.proj2)
        return set(self.variables.values()) - inputs

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

    def get_only_inputs_both(self):
        outputs = set()
        for op1 in self.op1s.values():
            outputs.add(op1.tgt)
        for op2 in self.op2s.values():
            outputs.add(op2.res)
        return set(self.variables.values()) - outputs

    def get_op1_targets(self):
        return {op.tgt: op_id for op_id, op in self.op1s.items()}

    def get_op2_targets(self):
        return {op.res: op_id for op_id, op in self.op2s.items()}


class Variable:
    def __init__(self, variable_id=None, type=None, name=None, identifiers=None):

        self.variable_id = variable_id
        self.type = type
        self.name = name
        self.symbol = sympy.Symbol(name)
        self.expression = None
        self.identifiers = identifiers

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.__repr__()

    def build_expression(self, decapode):
        """
            Builds an expression for a variable composed of symbols that are never the output of the same type of
            operations. If a variable is built up from a series of unary operations, the expression will be composed
            of variables that are never the output of another unary operations.

           Parameters
           ----------
           decapode: Decapode
                The decapode object for which we use its mappings to build an expression for a variable
           """
        # If the variable is built up from unary operations
        if not decapode.variable_op2_map_tree[self.variable_id]:
            while self.variable_id not in decapode.variable_expression_map_op1:
                for mapping_var_id, operation1 in decapode.variable_op1_map_linkedlist[self.variable_id].items():
                    if mapping_var_id in decapode.variable_expression_map_op1:
                        continue
                    elif mapping_var_id not in decapode.variable_expression_map_op1:
                        if operation1[0].src.variable_id in decapode.variable_expression_map_op1:
                            decapode.variable_expression_map_op1[mapping_var_id] = operation1[0].function_symbol(
                                decapode.variable_expression_map_op1[operation1[0].src.variable_id]
                            )
            self.expression = decapode.variable_expression_map_op1[self.variable_id]

        # If the variable is built up from binary operations
        elif decapode.variable_op2_map_tree[self.variable_id]:
            while self.variable_id not in decapode.variable_expression_map_op2:
                for mapping_var_id, operation2 in decapode.variable_op2_map_tree[self.variable_id].items():
                    if mapping_var_id in decapode.variable_expression_map_op2:
                        continue
                    elif mapping_var_id not in decapode.variable_expression_map_op2:
                        if (operation2[0].proj1.variable_id in decapode.variable_expression_map_op2 and
                            operation2[0].proj2.variable_id in decapode.variable_expression_map_op2):
                            proj1_expression = decapode.variable_expression_map_op2[operation2[0].proj1.variable_id]
                            proj2_expression = decapode.variable_expression_map_op2[operation2[0].proj2.variable_id]

                            decapode.variable_expression_map_op2[mapping_var_id] = (
                                perform_binary_operation_sympy(operation2[0].function_str, proj1_expression,
                                                               proj2_expression))
            self.expression = decapode.variable_expression_map_op2[self.variable_id]

        # It's a base-level variable and not the output of both unary and binary operations
        else:
            self.expression = decapode.variable_expression_map_both_op[self.variable_id]

    # Since this method relies on all variable expressions being accounted for the in the mappings, we have to run
    # build expression for each variable first before breaking down each non-base level variable in each variable's
    # expression
    def break_down_variables(self, decapode):
        """
            Breaks down each non base-level variable present in an expression. If a variable is built up from unary
            operations, the expression is broken down into variables that are never the output of another unary
            operation. However, it may be the case that these broken down variables are the result of a series
            of binary operations. This method helps break down variables built up from the other type of operations.

           Parameters
           ----------
           decapode: Decapode
                The decapode object for which we use its mappings to build an expression for a variable
           """
        var_set_symbols = {free_symbol for free_symbol in self.expression.free_symbols}
        while not var_set_symbols.issubset(decapode.set_base_symbols):
            for free_symbol in var_set_symbols:
                # if the free symbol is not a base level variable and is an output of an operation
                if free_symbol not in decapode.set_base_symbols:
                    free_symbol_var_id = next(
                        var.variable_id for var in decapode.variables.values() if var.name == str(free_symbol))

                    # If the non-base level free symbol is the result of a binary operation
                    if decapode.variable_op2_map_tree[free_symbol_var_id]:
                        self.expression = self.expression.subs(free_symbol,
                                                               decapode.variable_expression_map_op2[free_symbol_var_id])

                    # If the non-base level free symbol is the result of a unary operation
                    elif decapode.variable_op1_map_linkedlist[free_symbol_var_id]:
                        self.expression = self.expression.subs(free_symbol,
                                                               decapode.variable_expression_map_op1[free_symbol_var_id])
                    var_set_symbols = {free_symbol for free_symbol in self.expression.free_symbols}


def perform_binary_operation_sympy(operator, proj1, proj2):
    if operator == '/':
        return proj1 / proj2
    elif operator == '*':
        return proj1 * proj2
    elif operator == '+':
        return proj1 + proj2
    elif operator == '-':
        return proj1 - proj2
    elif operator == '^':
        return proj1 ** proj2


class TangentVariable(Variable):
    def __init__(self, tangent_id, incl_var_id):
        self.tangent_id = tangent_id
        self.incl_var_id = incl_var_id
        self.src_var_id = None


class Summation:
    def __init__(self, summation_id, summands, result_var_id):
        self.summation_id = summation_id
        self.summands = summands
        self.result_var_id = result_var_id
        self.sum = None

    # Can only run this after expressions have been built and variables have been broken down for each variable
    def add_variables(self):
        self.sum = self.summands[0].var.expression
        for summand in self.summands[1:]:
            self.sum = self.sum + summand.var.expression


class Summand:
    def __init__(self, summand_id, summand_var_id, summation_id, var):
        self.summand_id = summand_id
        self.summand_var_id = summand_var_id
        self.summation_id = summation_id
        self.var = var


class Op1:
    def __init__(self, src, tgt, op1):
        self.src = src
        self.tgt = tgt
        self.op1 = op1
        self.function_symbol = sympy.Function(op1)

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
        self.function_symbol = sympy.Function(op2)
        self.function_str = op2

    def __repr__(self):
        return f'Op2({self.proj1}, {self.proj2}, {self.res}, {self.op2})'

    def __str__(self):
        return self.__repr__()
