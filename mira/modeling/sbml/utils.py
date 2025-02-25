from typing import Optional
from fractions import Fraction

import sympy as sp
import bioregistry
from libsbml import (
    CVTerm,
    ASTNode,
    BIOLOGICAL_QUALIFIER,
    MODEL_QUALIFIER,
    AST_FUNCTION,
    AST_REAL,
)

from mira.metamodel import expression_to_mathml, SympyExprStr, Distribution
from mira.sources.sbml.processor import distribution_map
from mira.sources.sbml.utils import SBML_UNITS
from mira.metamodel.utils import safe_parse_expr

# Mapping of unit names within MIRA to sbml_unit_kind, multiplier, and scale
UNIT_MAP = {
    "day": ("second", 86400, 0),  # 1 day = 86400 seconds
    "year": ("second", 31536000, 0),  # 1 year = 31536000 seconds
    "liter": ("litre", 1, 0),
    "person": (
        "item",
        1,
        0,
    ),  # 'item' is used for dimensionless counts such as person
}

# Mapping of unit expressions to arbitrary unit id for assigning units to parameters
unit_def_to_name_map = {}


def get_uri(curie: str) -> Optional[str]:
    """Convert a curie to a URI, prioritizing the miriam format."""
    return bioregistry.get_iri(
        curie, priority=["miriam", "bioregistry", "default"]
    )


def create_biological_cv_term(curie, qualifier_predicate) -> Optional[CVTerm]:
    """Create a SBML biological resource term given a CURIE."""
    uri_resource = get_uri(curie)
    if not uri_resource:
        return None
    term = CVTerm()
    term.setQualifierType(BIOLOGICAL_QUALIFIER)
    term.setBiologicalQualifierType(qualifier_predicate)
    term.addResource(uri_resource)
    return term


def create_model_cv_term(resource, qualifier_predicate) -> Optional[CVTerm]:
    """Create a SBML model resource term given a CURIE."""
    uri_resource = get_uri(resource)
    if not uri_resource:
        return None
    term = CVTerm()
    term.setQualifierType(MODEL_QUALIFIER)
    term.setModelQualifierType(qualifier_predicate)
    term.addResource(uri_resource)
    return term


def convert_expression_mathml_export(expression: SympyExprStr) -> str:
    """Convert a sympy expression string into SBML compatible mathml"""
    mathml_expression = expression_to_mathml(expression)
    wrapped_mathml = f'<math xmlns="http://www.w3.org/1998/Math/MathML">{mathml_expression}</math>'
    return wrapped_mathml


def reverse_sbml_distribution_map():
    """This method returns a reverse mapping of sbml to probonto distributions"""
    probonto_to_sbml_dist_map = {}
    for sbml_dist_type, dist_values in distribution_map.items():
        sbml_original_params, (probonto_type, probonto_params) = dist_values
        probonto_to_sbml_dist_map[probonto_type] = (
            probonto_params,
            (sbml_dist_type, sbml_original_params),
        )
    return probonto_to_sbml_dist_map


def create_distribution_formula(dist: Distribution) -> Optional[ASTNode]:
    """Creates a distribution formula given a Distribution object"""
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


def set_compartment_units(units, model_compartment, sbml_model):
    unit_str_expression = str(units.expression)

    # dimensionless unit
    if unit_str_expression in unit_def_to_name_map:
        model_compartment.setUnits(unit_def_to_name_map[unit_str_expression])
        return

    unit_def = sbml_model.createUnitDefinition()
    unit_id = f"unit_{len(unit_def_to_name_map)}"
    unit_def.setId(unit_id)

    if unit_str_expression == "1":
        model_unit = unit_def.createUnit()
        model_unit.setKind(REVERSE_SBML_UNIT_MAP["dimensionless"])
        model_unit.setScale(0)
        model_unit.setMultiplier(1)
        model_unit.setExponent(0)
    else:
        # temporary solution as 1/(day*person) isn't classified as a fraction
        # unless re-convert it to a sympy.Expr by casting it as a string and
        # using safe_parse_expr
        numerator, denominator = sp.fraction(
            safe_parse_expr(unit_str_expression)
        )

        # If the numerator is not 1, handle it (e.g., units in the numerator)
        if numerator != 1:
            coefficient, expression = numerator.as_coeff_Mul()
            coeff_exists = False
            if coefficient != 1:
                num_multiplier, base = get_multiplier_and_base(coefficient)
                num_scale = int(sp.log(base, 10).evalf())
                coeff_exists = True
            for free_symbol in expression.expr_free_symbols:
                str_symbol = str(free_symbol)
                if str_symbol in UNIT_MAP:
                    unit_kind, multiplier, scale = UNIT_MAP[str_symbol]
                    model_unit = unit_def.createUnit()
                    model_unit.setKind(REVERSE_SBML_UNIT_MAP.get(unit_kind))
                    if coeff_exists:
                        model_unit.setScale(num_scale)
                        model_unit.setMultiplier(num_multiplier)
                    else:
                        model_unit.setScale(scale)
                        model_unit.setMultiplier(multiplier)
                    # use an exponent for 1 to represent element in numerator
                    model_unit.setExponent(1)

        # if denominator is 1 then that means it's not a fraction
        if denominator != 1:
            coefficient, expression = denominator.as_coeff_Mul()
            coeff_exists = False
            if coefficient != 1:
                denom_multiplier, base = get_multiplier_and_base(coefficient)
                denom_scale = int(sp.log(base, 10).evalf())
                coeff_exists = True
            for free_symbol in expression.expr_free_symbols:
                str_symbol = str(free_symbol)
                if str_symbol in UNIT_MAP:
                    unit_kind, multiplier, scale = UNIT_MAP[str_symbol]
                    model_unit = unit_def.createUnit()
                    model_unit.setKind(REVERSE_SBML_UNIT_MAP.get(unit_kind))
                    if coeff_exists:
                        model_unit.setScale(denom_scale)
                        model_unit.setMultplier(denom_multiplier)
                    else:
                        model_unit.setScale(scale)
                        model_unit.setMultiplier(multiplier)
                    # use an exponent for 1 to represent element in denominator
                    model_unit.setExponent(-1)

    unit_def_to_name_map[unit_str_expression] = unit_id
    model_compartment.setUnits(unit_def_to_name_map[unit_str_expression])


def get_multiplier_and_base(num):
    """Helper method to"""
    log_val = sp.log(num, 10)
    rounded_exp = round(log_val)
    base = 10**rounded_exp
    multiplier = num / base
    return float(multiplier), base


REVERSE_SBML_UNIT_MAP = {
    unit_name: unit_number for unit_number, unit_name in SBML_UNITS.items()
}
PROBONTO_TO_SBML_DISTRIBUTION_MAP = reverse_sbml_distribution_map()
