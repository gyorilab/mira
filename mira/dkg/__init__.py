"""Construction of domain knowledge graphs."""

import bioregistry

ASKEMO = bioregistry.Resource(
    name="ASKEM Ontology",
    prefix="askemo",
    description="A custom ontology to support the epidemiology use case in ASKEM.",
    pattern="^\\d{7}$",
)


def add_resource(resource: Resource) -> None:
    """Add a resource to the default registry during current runtime."""
    manager = bioregistry.manager
    if resource.prefix in manager.registry:
        raise KeyError
    manager.registry[resource.prefix] = resource
    if resource.has_canonical:
        manager.canonical_for.setdefault(resource.has_canonical, []).append(resource.prefix)
    if resource.provides:
        manager.provided_by.setdefault(resource.provides, []).append(resource.prefix)
    if resource.part_of:
        manager.has_parts.setdefault(resource.part_of, []).append(resource.prefix)


add_resource(ASKEMO)
