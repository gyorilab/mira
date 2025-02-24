from typing import Optional

import bioregistry
import libsbml

from mira.metamodel import expression_to_mathml, SympyExprStr


def get_uri(curie: str) -> Optional[str]:
    """Convert a curie to a URI, prioritizing the miriam format."""
    return bioregistry.get_iri(
        curie, priority=["miriam", "bioregistry", "default"]
    )


def create_biological_cv_term(
    curie, qualifier_predicate
) -> Optional[libsbml.CVTerm]:
    """Create a SBML biological resource term given a CURIE."""
    uri_resource = get_uri(curie)
    if not uri_resource:
        return None
    term = libsbml.CVTerm()
    term.setQualifierType(libsbml.BIOLOGICAL_QUALIFIER)
    term.setBiologicalQualifierType(qualifier_predicate)
    term.addResource(uri_resource)
    return term


def create_model_cv_term(
    resource, qualifier_predicate
) -> Optional[libsbml.CVTerm]:
    """Create a SBML model resource term given a CURIE."""
    uri_resource = get_uri(resource)
    if not uri_resource:
        return None
    term = libsbml.CVTerm()
    term.setQualifierType(libsbml.MODEL_QUALIFIER)
    term.setModelQualifierType(qualifier_predicate)
    term.addResource(uri_resource)
    return term


def convert_expression_mathml_export(expression: SympyExprStr) -> str:
    """Convert a sympy expression string into SBML compatible mathml"""
    mathml_expression = expression_to_mathml(expression)
    wrapped_mathml = f'<math xmlns="http://www.w3.org/1998/Math/MathML">{mathml_expression}</math>'
    return wrapped_mathml
