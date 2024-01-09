from pathlib import Path

import pysd
from pysd.translators.vensim.vensim_file import VensimFile
import requests
import sympy
import re

from mira.metamodel import *
from mira.metamodel.utils import safe_parse_expr
from mira.metamodel import Concept, TemplateModel
from mira.sources.util import (
    parameter_to_mira,
    transition_to_templates,
    get_sympy,
)

STOP_CHARACTER = "\\\\\\---///Sketchinformation-donotmodifyanythingexceptnames"
CONTROL_DELIMETER = "********************************************************"
NEW_CONTROL_DELIMETER = (
    " ******************************************************** .Control "
    "********************************************************"
)

CONTROL_VARIABLE_NAMES = {"FINALTIME", "INITIALTIME", "SAVEPER", "TIMESTEP"}
INTEG_FUNCTION = sympy.Function("Integ")

SEIR_URL = "https://metasd.com/wp-content/uploads/2020/03/SEIR-SS-growth3.mdl"
CHEWING_URL = "https://metasd.com/wp-content/uploads/2020/03/chewing-1.mdl"
SIR_URL = "https://raw.githubusercontent.com/SDXorg/test-models/master/samples/SIR/SIR.mdl"

EXAMPLE_DIRECTORY = Path(__file__).parent / "example_mdl"
COMMUNITY_CORONA_8_PATH = EXAMPLE_DIRECTORY / "community corona 8.mdl"
COVID_19_US_PATH = EXAMPLE_DIRECTORY / "Covid19US v2tf.mdl"
SIR_PATH = EXAMPLE_DIRECTORY / "sir.mdl"
SEIR_PATH = EXAMPLE_DIRECTORY / "seir-growth.mdl"


# If we are retrieving the contents of a mdl file hosted online, decode the content in bytes to
# strings
# def process_bytes_to_str(byte_object):
#     return (
#         byte_object.decode()
#         .replace("\r\n", "")
#         .replace("\t", "")
#         .replace(" ", "")
#         .replace('"', "")
#         .replace("&", "and")
#     )
#
#
# # Process each string in the file if we are loading a mdl file
# def process_str(text):
#     return (
#         text.replace("\r\n", "")
#         .replace("\t", "")
#         .replace(" ", "")
#         .replace('"', "")
#         .replace("&", "and")
#         .replace("\n", "")
#     )
#
#
# # test to see if the current string contains variable information or metadata
# def is_content_text(text):
#     if "|" in text or "~" in text or "{UTF-8}" in text or not text:
#         return False
#     else:
#         return True
#
#
# # converts the expression of a variable into sympy parseable strings
# def convert_expression_text(old_expression_text, converted_var_name_map):
#     for old_var_name, new_var_name in converted_var_name_map.items():
#         if old_var_name != new_var_name:
#             old_expression_text = old_expression_text.replace(
#                 old_var_name, new_var_name
#             )
#     return old_expression_text.replace("^", "**")
#
#
# #
# # # modifies the list parameter and returns it
# def create_converted_variable_name_mapping(text_list):
#     convereted_var_name_map = {}
#     i = 0
#     while i < len(text_list):
#         text = text_list[i]
#         if text == STOP_CHARACTER:
#             break
#
#         if not is_content_text(text):
#             i += 1
#             if "\\" in text_list[i]:
#                 while text_list[i] != "|":
#                     i += 1
#             continue
#
#         if (
#             text[len(text) - 1] == "="
#             and text[:-1] not in CONTROL_VARIABLE_NAMES
#         ):
#             old_var_name = text[:-1]
#             new_var_name = old_var_name.replace("*", "_star_").replace(
#                 "/", "_fslash_"
#             )
#             convereted_var_name_map[old_var_name] = new_var_name
#             text_list[i] = new_var_name + "="
#
#             if "\\" in text_list[i + 1]:
#                 i += 1
#                 while "~" not in text_list[i]:
#                     i += 1
#                 continue
#             i += 2
#             continue
#         elif "INTEG" in text:
#             i += 3
#             continue
#         elif text == CONTROL_DELIMETER:
#             break
#     return text_list, convereted_var_name_map
#
#
# def parse_mdl_file(url_or_path, is_url=True):
#     text_list = []
#     if is_url:
#         data = requests.get(url_or_path).content
#         byte_stream = io.BytesIO(data)
#         byte_list = byte_stream.readlines()
#         text_list = list(map(process_bytes_to_str, byte_list))
#     else:
#         with open(url_or_path) as f:
#             for line in f:
#                 text_list.append(line)
#         text_list = list(map(process_str, text_list))
#
#     text_list, converted_ver_name_map = create_converted_variable_name_mapping(
#         text_list
#     )
#     var_dict = {}
#     i = 0
#
#     while i < len(text_list):
#         text = text_list[i]
#         if text == STOP_CHARACTER:
#             break
#         # The declaration of control variables is always 6 lines below the control delimiter
#         if text == CONTROL_DELIMETER:
#             i += 6
#             continue
#
#         # lines beginning with "~" are comments
#         # lines that have a "|" are a delimiter for variable declaration
#         # first line is always the encoding
#         # skip past empty strings
#         if not is_content_text(text):
#             i += 1
#
#             # handles multi-line comments
#             if "\\" in text_list[i] and text_list[i] != STOP_CHARACTER:
#                 while text_list[i] != "|":
#                     i += 1
#             continue
#
#         # TODO:Handle lookups and input series data, not highest priority
#         # regular variable
#         if (
#             text[len(text) - 1] == "="
#             and text[:-1] not in CONTROL_VARIABLE_NAMES
#         ):
#             var_name = text[:-1]
#             var_dict[var_name] = {"name": var_name}
#
#             # Handle expressions for variables that span multiple lines
#             if "\\" in text_list[i + 1]:
#                 i += 1
#                 built_expression_text = ""
#                 while "~" not in text_list[i]:
#                     built_expression_text += text_list[i].replace("\\", "")
#                     i += 1
#
#                 expression = safe_parse_expr(
#                     convert_expression_text(built_expression_text), SYMBOL_MAP
#                 )
#                 var_dict[var_name]["expression"] = expression
#                 continue
#
#             # Handle expressions for variables defined on one line
#             expression_text = convert_expression_text(
#                 text_list[i + 1], converted_ver_name_map
#             )
#             expression = safe_parse_expr(expression_text, SYMBOL_MAP)
#             var_dict[var_name]["expression"] = expression
#             i += 2
#
#         # variable with "INTEG" operator that performs integral, its declaration is multi-line
#         elif "INTEG" in text:
#             var_integ_declaration = text.split("=")
#             var_name = var_integ_declaration[0]
#             var_dict[var_name] = {"name": var_name}
#
#             expression = INTEG_FUNCTION(
#                 text_list[i + 1][:-1], text_list[i + 2][:-1]
#             )
#             var_dict[var_name]["expression"] = expression
#             i += 3
#
#         # control variables
#         else:
#             if "SAVEPER" not in text:
#                 control_var_declaration = text.split("=")
#                 var_name = control_var_declaration[0]
#                 value = control_var_declaration[1]
#
#                 var_dict[var_name] = {"name": var_name}
#                 var_dict[var_name]["value"] = value
#
#                 i += 1
#
#             # When we come across "SAVEPER", skip it and go to the next declared control variable
#             # as it's value is set to "TIMESTEP", however; "SAVEPER" is initialized before
#             # "TIMESTEP"
#             else:
#                 i += 6
#
#     # Add "SAVEPER" to var_dict here
#     var_dict["SAVEPER"] = {
#         "name": "SAVEPER",
#         "value": var_dict["TIMESTEP"]["value"],
#     }
#     return var_dict


def state_to_concept(state) -> Concept:
    name = state["Py Name"]
    description = state["Comment"]
    units = state["Units"]
    units_obj = Unit(expression=units)

    return Concept(name=name, units=units_obj, description=description)


def process_expression_text(expr_text, var_name_mapping, processed=False):
    # strip leading and trailing white spaces
    # remove spaces between operators and operands
    # just account for multiplication in sir example, will have to add other operators
    # replace space between two words that makeup a variable name with "_"
    aux_expr_text = (
        expr_text.strip().replace(" * ", "*").replace(" ", "_").lower()
    )
    if not processed:
        for i, j in var_name_mapping.items():
            var_name_mapping[i] = sympy.Symbol(j)
    sympy_expr = safe_parse_expr(aux_expr_text, var_name_mapping)
    return sympy_expr


def template_model_from_mdl_file_url(url) -> TemplateModel:
    import tempfile

    data = requests.get(url).content
    temp_file = tempfile.NamedTemporaryFile(
        mode="w+b", suffix=".mdl", delete=False
    )

    with temp_file as file:
        file.write(data)

    utf_encoding = "{UTF-8} "

    # for constants, can call function that returns the value of that constant in generated py file
    vensim_file = VensimFile(temp_file.name)
    model_split_text = vensim_file.model_text.split("|")
    model = pysd.read_vensim(temp_file.name)
    model_doc_df = model.doc

    old_new_pyname_map = dict(
        zip(model_doc_df["Real Name"], model_doc_df["Py Name"])
    )

    # for real_name, py_name in old_var_name_map.items():
    #     new_real_name = real_name.replace(" ", "").replace('"', "")
    #     # Add what will appear in old_expression to py_name to Symbol Mapping
    #     SYMBOL_MAP[new_real_name] = sympy.Symbol(py_name)

    new_var_expression_map = {}
    for text in model_split_text:
        if NEW_CONTROL_DELIMETER in text:
            break
        if "=" not in text:
            continue

        # first entry usually has encoding type
        # map expression to variable name
        if utf_encoding in text:
            text = text.replace(utf_encoding, "")
        var_declaration = text.split("~")[0].split("=")
        old_var_name = var_declaration[0].strip()
        old_text_expression = var_declaration[1]
        # old_text_expression = (
        #     var_declaration[1].replace(" ", "").replace('"', "")
        # )
        # new_sympy_expression = safe_parse_expr(old_text_expression, SYMBOL_MAP)
        new_var_expression_map[
            old_new_pyname_map[old_var_name]
        ] = old_text_expression
    states = model_doc_df[model_doc_df["Type"] == "Stateful"]
    mira_states = {}
    all_states = set()
    symbols = {}
    state_rate_map = {}
    state_sympy_map = {}
    # process states
    # identifiers and context missing
    # identify stateful, look at functions for each stateful
    # looking at signs of the equations for each rate law in an integ expression for a state tells
    # us what rate is incoming and outgoing
    # + variable means incoming rate and - means outgoing rate
    # TODO: how to tell between natural or controlled conversion?
    # maybe that rate law depends on two stateful variables
    # the state that which the rate is leaving from is the input, any other state
    # variable would be the controller

    # process states and build mapping of state to rate laws input or output.
    # structure of this mapping is key: state value: {input:[],output:[]} where the state
    # serves as input to the rate laws in the input list and serves as outputs to the rate laws
    # in the output list
    for index, state in states.iterrows():
        concept_state = state_to_concept(state)
        mira_states[concept_state.name] = concept_state
        all_states.add(concept_state.name)
        symbols[concept_state.name] = sympy.Symbol(concept_state.name)

        state_name = state["Py Name"]
        state_rate_map[state_name] = {"inputs": [], "outputs": []}
        state_expr_text = new_var_expression_map[state_name]
        state_arg_text = re.search("INTEG+ \( (.*),", state_expr_text).group(1)
        if index == 0:
            state_arg_sympy = process_expression_text(
                state_arg_text, old_new_pyname_map
            )
        else:
            state_arg_sympy = process_expression_text(
                state_arg_text, old_new_pyname_map, processed=True
            )

        state_sympy_map[state_name] = state_arg_sympy
        # TODO: Evalaute logic here to make sure it's correct
        if state_arg_sympy.args:
            # if it's just the negation of a single symbol
            if (
                sympy.core.numbers.NegativeOne() in state_arg_sympy.args
                and len(state_arg_sympy.args) == 2
            ):
                str_symbol = str(state_arg_sympy)
                state_rate_map[state_name]["outputs"].append(str_symbol[1:])
            else:
                for rate_free_symbol in state_arg_sympy.args:
                    str_rate_free_symbol = str(rate_free_symbol)
                    if "-" in str_rate_free_symbol:
                        state_rate_map[state_name]["outputs"].append(
                            str_rate_free_symbol[1:]
                        )
                    else:
                        state_rate_map[state_name]["inputs"].append(
                            str_rate_free_symbol
                        )
        else:
            # if it's just a symbol, args property will be empty
            state_rate_map[state_name]["inputs"].append(str(state_arg_sympy))

    # process initials, just append 0 to each state to represent state at timestamp 0
    mira_initials = {}
    for state_name, state_concept in mira_states.items():
        initial = Initial(
            concept=mira_states[state_name].copy(deep=True),
            expression=safe_parse_expr(state_name + "0"),
        )
        mira_initials[initial.concept.name] = initial

    # process parameters
    mira_parameters = {}
    for name, expression in new_var_expression_map.items():
        #  Variables whose values are only numeric are Mira Parameters
        if expression.replace(".", "").replace(" ", "").isdecimal():
            model_parameter_info = model_doc_df[model_doc_df["Py Name"] == name]
            parameter = {
                "id": name,
                "value": float(expression),
                "description": model_parameter_info["Comment"].values[0],
                "units": {
                    "expression": model_parameter_info["Units"].values[0]
                },
            }
            mira_parameters[name] = parameter_to_mira(parameter)

    # Calling model.run shows value of each parameter/state/rate-law at different time stamps
    # extract values for each state at time-stamp 0 to get values assigned to initial conditions
    state_initial_values = model.run().iloc[0]
    for name, param_val in state_initial_values.items():
        py_name = old_new_pyname_map.get(name)
        if py_name in mira_states:
            param_name = str(mira_initials[py_name].expression)
            param_description = "Total {} count at timestep 0".format(py_name)
            parameter = {
                "id": param_name,
                "value": param_val,
                "description": param_description,
                # TODO: Work on units later
                # "units": {
                #     "expression": str(mira_states[py_name].units)
                # }
            }
            mira_parameters[param_name] = parameter_to_mira(parameter)

    # construct transitions mapping that determine inputs and outputs states to a rate-law
    transition_map = {}
    first_iteration = True
    auxiliaries = model_doc_df[model_doc_df["Type"] == "Auxiliary"]
    for index, aux_tuple in auxiliaries.iterrows():
        if (
            aux_tuple["Subtype"] == "Normal"
            and aux_tuple["Real Name"] not in CONTROL_VARIABLE_NAMES
        ):
            rate_name = aux_tuple["Py Name"]
            inputs = []
            outputs = []
            controllers = []

            # TODO: Evaluate logic here, currently it seems backwards but works
            for state_name, in_out in state_rate_map.items():
                if rate_name in in_out["outputs"]:
                    inputs.append(state_name)
                if rate_name in in_out["inputs"]:
                    outputs.append(state_name)

            # go through outputs to get controllers. If the expression for determining a state
            # has multiple rate laws associated with its expression, classify it as a controller.
            # this maybe not be the correct logic
            for output in outputs:
                state_expr_sympy = state_sympy_map[output]
                if (
                    len(state_expr_sympy.args) > 1
                    and sympy.core.numbers.NegativeOne()
                    not in state_expr_sympy.args
                ):
                    controllers.append(output)

            if first_iteration:
                processed = False
                first_iteration = False
            else:
                processed = True
            text_expr = new_var_expression_map[rate_name]
            rate_expr = process_expression_text(
                text_expr, old_new_pyname_map, processed=processed
            )

            transition_map[rate_name] = {
                "name": rate_name,
                "expression": rate_expr,
                "input": inputs,
                "outputs": outputs,
                "controllers": controllers,
            }

    # TODO: calculate static templates using all and used states sets
    used_states = set()

    # Create templates from transitions
    templates = []
    id = 1
    for transition_name, transition in transition_map.items():
        input_concepts = [mira_states[transition["input"][0]].copy(deep=True)]
        output_concepts = [
            mira_states[transition["outputs"][0]].copy(deep=True)
        ]
        if transition["controllers"]:
            controller_concepts = [
                mira_states[transition["controllers"][0]].copy(deep=True)
            ]
        else:
            controller_concepts = []
        templates.extend(
            transition_to_templates(
                input_concepts,
                output_concepts,
                controller_concepts,
                transition["expression"],
                id,
                transition_name,
            )
        )
        id += 1

    # TODO: Remove need for switching template order for sir example
    templates[1], templates[0] = templates[0], templates[1]
    tm_description = model_split_text[0].split("~")[1]
    anns = Annotations(descriptin=tm_description)

    return TemplateModel(
        templates=templates,
        parameters=mira_parameters,
        initials=mira_initials,
        annotations=anns,
    )


if __name__ == "__main__":
    tm_sir = template_model_from_mdl_file_url(url=SIR_URL)
