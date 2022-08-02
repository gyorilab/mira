__all__ = ["Concept", "Template", "Provenance", "ControlledConversion"]

from pydantic import BaseModel, Field
from typing import List, Mapping, Optional


class Concept(BaseModel):
    name: str = Field(..., description="The name of the concept.")
    identifiers: Mapping[str, str] = Field(default_factory=dict,
                                           description="A mapping of namespaces to identifiers.")
    context: Mapping[str, str] = Field(default_factory=dict,
                                       description="A mapping of context keys to values.")


class Template(BaseModel):
    pass


class Provenance(BaseModel):
    pass


class ControlledConversion(Template):
    type: str = "ControlledConversion"
    controller: Concept
    subject: Concept
    outcome: Concept
    provenance: List[Provenance] = Field(default_factory=list)


class NaturalConversion(Template):
    type: str = "NaturalConversion"
    subject: Concept
    outcome: Concept
    provenance: List[Provenance] = Field(default_factory=list)