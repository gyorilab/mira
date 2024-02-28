"""This module implements an API interface for retrieving Vensim models by Ventana Systems
denoted by the .mdl extension through a locally downloaded file or URL. We then
convert the Vensim model into a generic pysd model object that will be parsed and converted to an
equivalent MIRA template model. We preprocess the vensim file to extract variable expressions.

Vensim model documentation:https://www.vensim.com/documentation/sample_models.html

Repository of sample Vensim models: https://github.com/SDXorg/test-models/tree/master/samples
"""

import tempfile
import re
import typing as t

import pysd
from pysd.translators.vensim.vensim_file import VensimFile
import requests

from mira.metamodel import TemplateModel, Initial
from mira.sources.system_dynamics.pysd import (
    template_model_from_pysd_model, ifthenelse_to_piecewise
)

__all__ = ["template_model_from_mdl_file", "template_model_from_mdl_url"]

NEW_CONTROL_DELIMETER = (
    " ******************************************************** .Control "
    "********************************************************"
)
SKETCH_DELIMETER = (
    "\\\---/// Sketch information - do not modify anything except names"
)
UTF_ENCODING = "{UTF-8} "

CONTROL_VARIABLES = {"SAVEPER", "FINAL TIME", "INITIAL TIME", "TIME STEP"}


def template_model_from_mdl_file(fname, *, grounding_map=None, initials=None) -> TemplateModel:
    """Return a template model from a local Vensim file

    Parameters
    ----------
    fname : str or pathlib.Path
        The path to the local Vensim file
    grounding_map: dict[str, Concept]
        A grounding map, a map from label to Concept

    Returns
    -------
    :
        A MIRA template model
    """
    pysd_model = pysd.read_vensim(fname)
    vensim_file = VensimFile(fname)
    expression_map, initials_map = extract_vensim_variable_expressions(vensim_file.model_text)
    if initials:
        initials_map.update(initials)
    return template_model_from_pysd_model(
        pysd_model,
        expression_map,
        grounding_map=grounding_map,
        initials_map=initials_map,
    )


def template_model_from_mdl_url(url, *, grounding_map=None, initials=None) -> TemplateModel:
    """Return a template model from a Vensim file provided by an url

    Parameters
    ----------
    url : str
        The url to the mdl file
    grounding_map: dict[str, Concept]
        A grounding map, a map from label to Concept

    Returns
    -------
    :
        A MIRA Template Model
    """
    data = requests.get(url).content
    temp_file = tempfile.NamedTemporaryFile(
        mode="w+b", suffix=".mdl", delete=False
    )

    with temp_file as file:
        file.write(data)

    return template_model_from_mdl_file(temp_file.name, grounding_map=grounding_map, initials=initials)


# look past control section
def extract_vensim_variable_expressions(model_text):
    """Method that extracts expressions for each variable in a Vensim file

    Parameters
    ----------
    model_text : str
        The plain-text information about the Vensim file

    Returns
    -------
    : dict[str,str]
        Mapping of variable name to string variable expression
    """
    expression_map = {}
    initial_values = {}

    # Model text is a single string that represents the entire contents of the Vensim model.
    # We split model text into a list with elements delimited by "|"
    # variable declaration in vensim files are delimited by the "|" character
    model_split_text = model_text.split("|")

    for text in model_split_text:
        # signifies end of model
        if SKETCH_DELIMETER in text:
            break

        # signifies start of control section, continue
        if NEW_CONTROL_DELIMETER in text:
            continue

        # if no variable declaration, continue
        if "=" not in text:
            continue

        # first entry usually has encoding type
        if UTF_ENCODING in text:
            text = text.replace(UTF_ENCODING, "")

        # Throw away every text after the "~" and split the remaining text by "=" to get
        # variable name and accompanying expression
        var_declaration = text.split("~")[0].split("=")
        old_var_name = var_declaration[0].strip()
        text_expression = var_declaration[1].strip()

        # account for variables with expressions that have "=" in them besides the
        # initial "=" character for var declaration, stitch together the expression
        if len(var_declaration) > 2:
            for part_expression_text in var_declaration[2:]:
                text_expression += "=" + part_expression_text

        # vensim has several builtin functions, like MIN(), MAX(), XIDZ(), INTEG()
        #   we pass these along for sympy to just consider like function calls.
        # Hackathon file does not use any built-in functions that don't take a single argument
        # Can account for single argument Vensim functions as well
        # List of Vensim functions: https://www.vensim.com/documentation/22300.html
        # "INTEG" is the keyword used to define a state/stock
        # however, we can't yet handle if/then/else constructs, so we skip them
        if "if then else" in text_expression.lower():
            text_expression = ifthenelse_to_piecewise(text_expression)

        # If there's an INTEG expression, we can extract an initial value,
        # otherwise, it is none.
        initial = None

        # If we come across a state, get the expression for the state only

        # For the hackathon Vensim file, we can use a new regex that gets not only the expression
        # but the initial value as well. Because when pysd ingests the hackathon Vensim file,
        # it will have 44 initial values for only 19 states.
        if "INTEG" in text_expression:
            match = re.search(r"\(([^,]+),\s*(.*)?\)", text_expression)
            text_expression = match.group(1)
            initial = match.group(2)
            print(old_var_name, initial)

        expression_map[old_var_name] = text_expression

        # CTH: I couldn't find where this normalization happens
        # between the vensim and pysd code, so I added it again here.
        # also, the initial value might be an expression that needs normalizing
        initial_values[_norm(old_var_name)] = initial and _norm(initial)

    # remove any control variables listed past the control section that were added to the
    # expression map
    for control_var in CONTROL_VARIABLES:
        expression_map.pop(control_var)

    return expression_map, initial_values


def _norm(s):
    return s.lower().replace(" ", "_")
