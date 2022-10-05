"""Construction of domain knowledge graphs."""

import bioregistry

ASKEMO = bioregistry.Resource(
    name="ASKEM Ontology",
    prefix="askemo",
    description="A custom ontology to support the epidemiology use case in ASKEM.",
    pattern="^\\d{7}$",
)
bioregistry.manager.add_resource(ASKEMO)
