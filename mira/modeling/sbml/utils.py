from typing import Optional, Tuple, Dict, Union
from fractions import Fraction

import sympy as sp
import bioregistry
from libsbml import (
    CVTerm,
    ASTNode,
    Model as LibSBMLModel,
    UnitDefinition,
    Parameter,
    Species,
    BIOLOGICAL_QUALIFIER,
    MODEL_QUALIFIER,
    AST_FUNCTION,
    AST_REAL,
)

from mira.metamodel import (
    expression_to_mathml,
    SympyExprStr,
    Distribution,
    Unit,
)
from mira.sources.sbml.processor import distribution_map
from mira.sources.sbml.utils import SBML_UNITS
from mira.metamodel.utils import safe_parse_expr

# Mapping of unit names within MIRA to sbml_unit_kind, multiplier, and scale
UNIT_MAP = {
    "day": ("second", 86400, 0),  # 1 day = 86400 seconds
    "year": ("second", 31536000, 0),  # 1 year = 31536000 seconds
    "liter": ("litre", 1, 0),
    "person": ("item", 1, 0),  # 'item' is used for dimensionless counts such as person
}


def get_uri(curie: str) -> Optional[str]:
    """
    Convert a CURIE to a URI, prioritizing the miriam format.

    Parameters
    ----------
    curie :
        The CURIE to convert

    Returns
    -------
    :
        The converted CURIE
    """
    return bioregistry.get_iri(
        curie, priority=["miriam", "bioregistry", "default"]
    )


def create_biological_cv_term(
    curie: str, qualifier_predicate: int
) -> Optional[CVTerm]:
    """
    Create a SBML biological resource term given a CURIE and qualifier predicate.

    Parameters
    ----------
    curie :
        The CURIE to create a resource out of.
    qualifier_predicate :
        The qualifier type of the created term

    Returns
    -------
    :
        The created biological CVTerm.
    """
    uri_resource = get_uri(curie)
    if not uri_resource:
        return None
    term = CVTerm()
    term.setQualifierType(BIOLOGICAL_QUALIFIER)
    term.setBiologicalQualifierType(qualifier_predicate)
    term.addResource(uri_resource)
    return term


def create_model_cv_term(curie, qualifier_predicate) -> Optional[CVTerm]:
    """
    Create a SBML model resource term given a CURIE and qualifier predicate.

    Parameters
    ----------
    curie :
        The CURIE to create a resource out of
    qualifier_predicate

    Returns
    -------
    :
        The created model CVTerm
    """
    uri_resource = get_uri(curie)
    if not uri_resource:
        return None
    term = CVTerm()
    term.setQualifierType(MODEL_QUALIFIER)
    term.setModelQualifierType(qualifier_predicate)
    term.addResource(uri_resource)
    return term


def convert_expression_mathml_export(expression: SympyExprStr) -> str:
    """
    Convert sympy expressions into equivalent mathml expressions wrapping
    the mathml expression in a math tag with accompanying namespace for export.

    Parameters
    ----------
    expression :
        The sympy expression to be converted into mathml

    Returns
    -------
    :
        The xml string representing the mathml expression
    """
    mathml_expression = expression_to_mathml(expression)
    wrapped_mathml = f'<math xmlns="http://www.w3.org/1998/Math/MathML">{mathml_expression}</math>'
    return wrapped_mathml


def reverse_sbml_distribution_map() -> Dict[str, Tuple]:
    """
    Helper method to reverse the mapping of SBML to probonto distributions.

    Returns
    -------
    :
        A mapping of probonto to SBML distributions.
    """
    probonto_to_sbml_dist_map = {}
    for sbml_dist_type, dist_values in distribution_map.items():
        sbml_original_params, (probonto_type, probonto_params) = dist_values
        probonto_to_sbml_dist_map[probonto_type] = (
            probonto_params,
            (sbml_dist_type, sbml_original_params),
        )
    return probonto_to_sbml_dist_map


def create_distribution_ast_node(dist: Distribution) -> Optional[ASTNode]:
    """
    Creates a distribution formula in the form of an abstract syntax tree node
    given a Distribution object.

    Parameters
    ----------
    dist :
        The distribution to create an AST node out of.

    Returns
    -------
    :
        The AST Node that represents the distribution
    """
    if dist.type in PROBONTO_TO_SBML_DISTRIBUTION_MAP:
        probonto_params, (
            sbml_name,
            sbml_params,
        ) = PROBONTO_TO_SBML_DISTRIBUTION_MAP[dist.type]
        func_node = ASTNode(AST_FUNCTION)
        func_node.setName(sbml_name)
        for param in probonto_params:
            value = dist.parameters.get(param)
            param_node = ASTNode()
            param_node.setType(AST_REAL)
            try:
                param_node.setValue(float(str(value)))
            except ValueError:
                # Cannot convert string fractions to float so use the
                # Fraction class
                param_node.setValue(float(Fraction(str(value))))
            func_node.addChild(param_node)
        return func_node
    return None


def set_element_units(
    units: Unit,
    model_element: Union[Species, Parameter],
    sbml_model: LibSBMLModel,
    unit_expression_to_id_map: Dict[str, str],
):
    """
    Creates a unit definition given a MIRA unit object and sets a libSBML model element's
    units. More in-depth, this method calculates the multiplier, scale, kind,
    and exponent of each symbol/unit in a unit expression/unit definition.

    Parameters
    ----------
    units :
        The units associated with a MIRA template model compartment.
    model_element :
        The libSBML model element that will have its units set.
    sbml_model :
        The SBML model that we are building up when exporting SBML.
    unit_expression_to_id_map :
        Mapping of unit expressions as strings to unit ids

    """
    unit_str_expression = str(units.expression)

    # Index mapping on expression in string format
    if unit_str_expression in unit_expression_to_id_map:
        model_element.setUnits(unit_expression_to_id_map[unit_str_expression])
        return

    unit_def = sbml_model.createUnitDefinition()
    unit_id = f"unit_{len(unit_expression_to_id_map)}"
    unit_def.setId(unit_id)

    # Process dimensionless unit
    if unit_str_expression == "1":
        model_unit = unit_def.createUnit()
        model_unit.setKind(REVERSE_SBML_UNIT_MAP["dimensionless"])
        model_unit.setScale(0)
        model_unit.setMultiplier(1)
        model_unit.setExponent(0)
    else:
        # 1/(day*person) isn't classified as a fraction
        # unless we re-convert it to a sympy.Expr by casting it as a string and
        # using safe_parse_expr
        numerator, denominator = sp.fraction(
            safe_parse_expr(unit_str_expression)
        )

        # If the numerator is not 1, handle it (e.g., units in the numerator)
        if numerator != 1:
            process_fraction_term(numerator, unit_def, 1)

        # if denominator is 1 then that means the expression isn't a fraction
        if denominator != 1:
            # use an exponent for 1 to represent element in denominator
            process_fraction_term(denominator, unit_def, -1)

    unit_expression_to_id_map[unit_str_expression] = unit_id
    model_element.setUnits(unit_expression_to_id_map[unit_str_expression])


def process_fraction_term(fraction_term: sp.Expr, unit_def: UnitDefinition, exponent: int):
    """
    Helper method to define the units used in a unit definition by processing
    the numerator and denominator in a TemplateModel object's unit's expression.

    Parameters
    ----------
    fraction_term :
        The sympy expression to process
    unit_def :
        The libSBML unit definition object that will have its units defined
    exponent :
        The exponent to set the unit to. Currently, it's 1 for symbols in the numerator
        and -1 for symbols in the denominator.
    """
    coefficient, expression = fraction_term.as_coeff_Mul()
    coefficient_exists = False
    if coefficient != 1:
        coefficient_multiplier, base = get_multiplier_and_base(coefficient)
        coefficient_scale = int(sp.log(base, 10).evalf())
        coefficient_exists = True
    for free_symbol in expression.free_symbols:
        str_symbol = str(free_symbol)
        if str_symbol in UNIT_MAP:
            unit_kind, multiplier, scale = UNIT_MAP[str_symbol]
            model_unit = unit_def.createUnit()
            model_unit.setKind(REVERSE_SBML_UNIT_MAP.get(unit_kind))
            if coefficient_exists:
                model_unit.setScale(coefficient_scale)
                model_unit.setMultiplier(coefficient_multiplier)
            else:
                model_unit.setScale(scale)
                model_unit.setMultiplier(multiplier)
            model_unit.setExponent(exponent)


def get_multiplier_and_base(num: sp.Expr) -> Tuple[float, sp.Expr]:
    """
    Helper method to retrieve the multiplier and base of a sympy number
    rounded to the nearest power of ten.

    Parameters
    ----------
    num :
        The number to retrieve the multiplier and base for

    Returns
    -------
    :
        A tuple containing the multiplier and base.
    """
    log_value = sp.log(num, 10)
    rounded_exponent = round(log_value)
    base = 10**rounded_exponent
    multiplier = num / base
    return float(multiplier), base


REVERSE_SBML_UNIT_MAP = {
    unit_name: unit_number for unit_number, unit_name in SBML_UNITS.items()
}
PROBONTO_TO_SBML_DISTRIBUTION_MAP = reverse_sbml_distribution_map()
