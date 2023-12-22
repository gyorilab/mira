import io
from pathlib import Path

import requests
import sympy

from mira.metamodel.utils import safe_parse_expr


STOP_CHARACTER = "\\\\\\---///Sketchinformation-donotmodifyanythingexceptnames"
CONTROL_DELIMETER = "********************************************************"
INTEG_FUNCTION = sympy.Function("INTEG")
SYMBOL_MAP = {"alpha": sympy.Symbol("α"), "beta": sympy.Symbol("β")}
CONTROL_VARIABLE_NAMES = {"FINALTIME", "INITIALTIME", "SAVEPER", "TIMESTEP"}

SEIR_URL = "https://metasd.com/wp-content/uploads/2020/03/SEIR-SS-growth3.mdl"
CHEWING_URL = "https://metasd.com/wp-content/uploads/2020/03/chewing-1.mdl"
HERE = Path(__file__).parent
CORONOA_FILE_NAME = HERE / "community corona 8.mdl"




def process_bytes_to_str(byte_object):
    return (
        byte_object.decode()
        .replace("\r\n", "")
        .replace("\t", "")
        .replace(" ", "")
        .replace('"', "")
        .replace("&", "and")
    )


def process_str(text):
    return (
        text.replace("\r\n", "")
        .replace("\t", "")
        .replace(" ", "")
        .replace('"', "")
        .replace("&", "and")
        .replace("\n", "")
    )


def parse_mdl_file(url_or_path, is_url=True):
    text_list = []
    if is_url:
        data = requests.get(url_or_path).content
        byte_stream = io.BytesIO(data)
        byte_list = byte_stream.readlines()
        text_list = list(map(process_bytes_to_str, byte_list))
    else:
        with open(CORONOA_FILE_NAME) as f:
            for line in f:
                text_list.append(line)
        text_list = list(map(process_str, text_list))

    var_dict = {}
    i = 0

    while i < len(text_list):
        text = text_list[i]
        # lines beginning with ~ are comments
        if text == STOP_CHARACTER:
            break
        # The declaration of control variables is always 6 lines below the control delimiter
        if text == CONTROL_DELIMETER:
            i += 6
            continue
        if "|" in text or "~" in text or "{UTF-8}" in text or not text:
            i += 1
            continue

        # regular variable
        if (
            text[len(text) - 1] == "="
            and text[:-1] not in CONTROL_VARIABLE_NAMES
        ):
            var_name = text[:-1]
            # Some variable names have operators in the name and g*'s expression involves variables
            # so it's not possible to parse with safe_parse_expr such as "/"
            if "g*" in var_name or "/" in var_name or "*" in var_name:
                i += 2
                continue

            var_dict[var_name] = {"name": var_name}

            # TODO: Handle case where expressions not involving INTEG span multiple lines
            expression = safe_parse_expr(text_list[i + 1], SYMBOL_MAP)
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

            # When we come across "SAVEPER", just skip it as it's value is set to "TIMESTEP"
            # however, "SAVEPER" is initialized before "TIMESTEP"
            else:
                i += 2

    # Add "SAVEPER" to var_dict here
    var_dict["SAVEPER"] = {
        "name": "SAVEPER",
        "value": var_dict["TIMESTEP"]["value"],
    }
    return var_dict


if __name__ == "__main__":
    j = parse_mdl_file(CORONOA_FILE_NAME, is_url=False)
    print()
