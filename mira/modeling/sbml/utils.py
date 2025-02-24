from typing import Optional

import bioregistry
import libsbml

def get_uri(curie: str) -> Optional[str]:
    """Convert a curie to a URI, prioritizing the miriam format."""
    return bioregistry.get_iri(
        curie, priority=["miriam", "bioregistry", "default"]
    )


def create_biological_cv_term(
    resource, qualifier_predicate
) -> Optional[libsbml.CVTerm]:
    uri_resource = get_uri(resource)
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
    uri_resource = get_uri(resource)
    if not uri_resource:
        return None
    term = libsbml.CVTerm()
    term.setQualifierType(libsbml.MODEL_QUALIFIER)
    term.setModelQualifierType(qualifier_predicate)
    term.addResource(uri_resource)
    return term