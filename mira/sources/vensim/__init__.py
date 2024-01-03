import io
from pathlib import Path

import requests
import sympy

from mira.metamodel.utils import safe_parse_expr


STOP_CHARACTER = "\\\\\\---///Sketchinformation-donotmodifyanythingexceptnames"
CONTROL_DELIMETER = "********************************************************"
INTEG_FUNCTION = sympy.Function("INTEG")
SYMBOL_MAP = {
    "alpha": sympy.Symbol("α"),
    "beta": sympy.Symbol("β"),
}
CONTROL_VARIABLE_NAMES = {"FINALTIME", "INITIALTIME", "SAVEPER", "TIMESTEP"}
CONVERTED_VAR_NAME_MAP = {}

SEIR_URL = "https://metasd.com/wp-content/uploads/2020/03/SEIR-SS-growth3.mdl"
CHEWING_URL = "https://metasd.com/wp-content/uploads/2020/03/chewing-1.mdl"

EXAMPLE_DIRECTORY = Path(__file__).parent / "example_mdl"
COMMUNITY_CORONA_8_PATH = EXAMPLE_DIRECTORY / "community corona 8.mdl"
COVID_19_US_PATH = EXAMPLE_DIRECTORY / "Covid19US v2tf.mdl"


# If we are retrieving the contents of a mdl file hosted online, decode the content in bytes to
# strings
def process_bytes_to_str(byte_object):
    return (
        byte_object.decode()
        .replace("\r\n", "")
        .replace("\t", "")
        .replace(" ", "")
        .replace('"', "")
        .replace("&", "and")
    )


# Process each string in the file if we are loading an mdl file
def process_str(text):
    return (
        text.replace("\r\n", "")
        .replace("\t", "")
        .replace(" ", "")
        .replace('"', "")
        .replace("&", "and")
        .replace("\n", "")
    )


# test to see if the current string contains variable information or metadata
def is_content_text(text):
    if "|" in text or "~" in text or "{UTF-8}" in text or not text:
        return False
    else:
        return True


# converts the expression of a variable into sympy parseable strings
def convert_expression_text(old_expression_text):
    new_expression_text = old_expression_text
    for old_var_name, new_var_name in CONVERTED_VAR_NAME_MAP.items():
        if old_var_name != new_var_name:
            new_expression_text = new_expression_text.replace(
                old_var_name, new_var_name
            )
    return new_expression_text.replace("^", "**")


# modifies the list parameter, doesn't return anything
def create_converted_variable_name_mapping(text_list):
    i = 0
    while i < len(text_list):
        text = text_list[i]
        if text == STOP_CHARACTER:
            break

        if not is_content_text(text):
            i += 1
            if "\\" in text_list[i]:
                while text_list[i] != "|":
                    i += 1
            continue

        if (
            text[len(text) - 1] == "="
            and text[:-1] not in CONTROL_VARIABLE_NAMES
        ):
            old_var_name = text[:-1]
            new_var_name = old_var_name.replace("*", "_star_").replace(
                "/", "_fslash_"
            )
            CONVERTED_VAR_NAME_MAP[old_var_name] = new_var_name
            text_list[i] = new_var_name + "="

            if "\\" in text_list[i + 1]:
                i += 1
                while "~" not in text_list[i]:
                    i += 1
                continue
            i += 2
            continue
        elif "INTEG" in text:
            i += 3
            continue
        elif text == CONTROL_DELIMETER:
            break


def parse_mdl_file(url_or_path, is_url=True):
    text_list = []
    if is_url:
        data = requests.get(url_or_path).content
        byte_stream = io.BytesIO(data)
        byte_list = byte_stream.readlines()
        text_list = list(map(process_bytes_to_str, byte_list))
    else:
        with open(url_or_path) as f:
            for line in f:
                text_list.append(line)
        text_list = list(map(process_str, text_list))

    create_converted_variable_name_mapping(text_list)
    var_dict = {}
    i = 0

    while i < len(text_list):
        text = text_list[i]
        if text == STOP_CHARACTER:
            break
        # The declaration of control variables is always 6 lines below the control delimiter
        if text == CONTROL_DELIMETER:
            i += 6
            continue

        # lines beginning with "~" are comments
        # lines that have a "|" are a delimiter for variable declaration
        # first line is always the encoding
        # skip past empty strings
        if not is_content_text(text):
            i += 1

            # handles multi-line comments
            if "\\" in text_list[i] and text_list[i] != STOP_CHARACTER:
                while text_list[i] != "|":
                    i += 1
            continue

        # TODO:Handle lookups and input series data
        # regular variable
        if (
            text[len(text) - 1] == "="
            and text[:-1] not in CONTROL_VARIABLE_NAMES
        ):
            var_name = text[:-1]
            var_dict[var_name] = {"name": var_name}

            # Handle expressions for variables that span multiple lines
            if "\\" in text_list[i + 1]:
                i += 1
                built_expression_text = ""
                while "~" not in text_list[i]:
                    built_expression_text += text_list[i].replace("\\", "")
                    i += 1

                expression = safe_parse_expr(
                    convert_expression_text(built_expression_text), SYMBOL_MAP
                )
                var_dict[var_name]["expression"] = expression
                continue

            # Handle expressions for variables defined on one line
            expression_text = convert_expression_text(text_list[i + 1])
            expression = safe_parse_expr(expression_text, SYMBOL_MAP)
            var_dict[var_name]["expression"] = expression
            i += 2

        # variable with "INTEG" operator that performs integral, its declaration is multi-line
        elif "INTEG" in text:
            var_integ_declaration = text.split("=")
            var_name = var_integ_declaration[0]
            var_dict[var_name] = {"name": var_name}

            expression = INTEG_FUNCTION(
                text_list[i + 1][:-1], text_list[i + 2][:-1]
            )
            var_dict[var_name]["expression"] = expression
            i += 3

        # control variables
        else:
            if "SAVEPER" not in text:
                control_var_declaration = text.split("=")
                var_name = control_var_declaration[0]
                value = control_var_declaration[1]

                var_dict[var_name] = {"name": var_name}
                var_dict[var_name]["value"] = value

                i += 1

            # When we come across "SAVEPER", skip it and go to the next declared control variable
            # as it's value is set to "TIMESTEP", however; "SAVEPER" is initialized before
            # "TIMESTEP"
            else:
                i += 6

    # Add "SAVEPER" to var_dict here
    var_dict["SAVEPER"] = {
        "name": "SAVEPER",
        "value": var_dict["TIMESTEP"]["value"],
    }

    return var_dict


if __name__ == "__main__":
    seir_variables = parse_mdl_file(SEIR_URL, is_url=True)
    chewing_variables = parse_mdl_file(CHEWING_URL, is_url=True)
    local_corona_variables = parse_mdl_file(
        COMMUNITY_CORONA_8_PATH, is_url=False
    )
