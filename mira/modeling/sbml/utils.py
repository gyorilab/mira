from typing import Optional
from fractions import Fraction

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
    if dist.type in probonto_to_sbml_distribution_map:
        probonto_params, (
            sbml_name,
            sbml_params,
        ) = probonto_to_sbml_distribution_map[dist.type]
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


probonto_to_sbml_distribution_map = reverse_sbml_distribution_map()
