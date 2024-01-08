from pathlib import Path

import pysd
from pysd.translators.vensim.vensim_file import VensimFile
import requests
import sympy

from mira.metamodel import *
from mira.metamodel.utils import safe_parse_expr
from mira.metamodel import Concept, TemplateModel
from mira.sources.util import parameter_to_mira, transition_to_templates

STOP_CHARACTER = "\\\\\\---///Sketchinformation-donotmodifyanythingexceptnames"
CONTROL_DELIMETER = "********************************************************"
NEW_CONTROL_DELIMETER = (
    " ******************************************************** .Control "
    "********************************************************"
)

SYMBOL_MAP = {
    "alpha": sympy.Symbol("α"),
    "beta": sympy.Symbol("β"),
}
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


def template_model_from_mdl_file(file_path, *, url=None) -> TemplateModel:
    if url:
        data = requests.get(url).content
        with open(file_path, "wb") as file:
            file.write(data)

    utf_encoding = "{UTF-8} "

    vensim_file = VensimFile(file_path)
    model_split_text = vensim_file.model_text.split("|")
    model = pysd.read_vensim(file_path)
    model_doc_df = model.doc

    old_var_name_map = dict(
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
            old_var_name_map[old_var_name]
        ] = old_text_expression

    states = model_doc_df[model_doc_df["Type"] == "Stateful"]
    mira_states = {}
    all_states = set()
    symbols = {}
    # process states
    # identifiers and context missing
    for index, state in states.iterrows():
        concept_state = state_to_concept(state)
        mira_states[concept_state.name] = concept_state
        all_states.add(concept_state.name)
        symbols[concept_state.name] = sympy.Symbol(concept_state.name)

    # process parameters
    mira_parameters = {}
    for name, expression in new_var_expression_map.items():
        #  Variables whose values are only numeric are Mira Parameters
        if expression.replace(".", "").isnumeric():
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

    # process initials
    # currently we just retrieve initials based on states
    mira_initials = {}
    for state in mira_states.values():
        try:
            initial = Initial(
                concept=mira_states[state.name].copy(deep=True),
                expression=state.name + "0",
            )
            mira_initials[initial.concept.name] = initial
        except TypeError:
            continue

    mira_observables = {}
    auxiliaries = model_doc_df[model_doc_df["Type"] == "Auxiliary"]
    for template_id, aux_tuple in enumerate(auxiliaries.iterrows()):
        aux = aux_tuple[1]
        if (
            aux["Subtype"] == "Normal"
            and aux["Real Name"] not in CONTROL_VARIABLE_NAMES
        ):
            aux_expr = new_var_expression_map[aux["Py Name"]]
            # strip leading and trailing white spaces
            # remove spaces between operators and operands
            # just account for multiplication in sir example, will have to generalize
            # replace space between two words that makeup a variable name with "_"
            aux_expr = aux_expr.strip().replace(" * ", "*").replace(" ", "_")
            observable_expr = safe_parse_expr(aux_expr)
            observable = Observable(
                name=aux["Py Name"],
                expression=observable_expr,
                display_name=aux["Py Name"],
            )
            mira_observables[observable.name] = observable

    # process transitions (Not done yet)
    used_states = set()
    templates_ = []
    auxiliaries = model_doc_df[model_doc_df["Type"] == "Auxiliary"]
    for template_id, aux_tuple in enumerate(auxiliaries.iterrows()):
        aux = aux_tuple[1]
        if (
            aux["Subtype"] == "Normal"
            and aux["Real Name"] not in CONTROL_VARIABLE_NAMES
        ):
            if aux["Real Name"] == "Recovering":
                input_concepts = [mira_states["infectious"]]
                output_concepts = [mira_states["recovered"]]
                controller_concepts = []
                rate_expr = safe_parse_expr(
                    new_var_expression_map[aux["Py Name"]], SYMBOL_MAP
                )

                templates_.extend(
                    transition_to_templates(
                        input_concepts,
                        output_concepts,
                        controller_concepts,
                        rate_expr,
                        template_id + 1,
                        aux["Real Name"],
                    )
                )

    tm_description = model_split_text[0].split("~")[1]
    anns = Annotations(descriptin=tm_description)

    return TemplateModel(
        templates=templates_,
        parameters=mira_parameters,
        initials=mira_initials,
        observables=mira_observables,
        annotations=anns,
    )


if __name__ == "__main__":
    tm_sir = template_model_from_mdl_file(SIR_PATH, url=SIR_URL)

