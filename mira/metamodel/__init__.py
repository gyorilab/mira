__all__ = ["Concept", "Template", "Provenance", "ControlledConversion",
           "NaturalConversion"]

import sys

from typing import List, Mapping

from pydantic import BaseModel, Field


class Concept(BaseModel):
    name: str = Field(..., description="The name of the concept.")
    identifiers: Mapping[str, str] = Field(default_factory=dict,
                                           description="A mapping of namespaces to identifiers.")
    context: Mapping[str, str] = Field(default_factory=dict,
                                       description="A mapping of context keys to values.")


class Template(BaseModel):
    @classmethod
    def from_json(cls, data) -> "Template":
        template_type = data.pop('type')
        stmt_cls = getattr(sys.modules[__name__], template_type)
        return stmt_cls(**data)


class Provenance(BaseModel):
    pass


class ControlledConversion(Template):
    type: str = Field("ControlledConversion", const=True)
    controller: Concept
    subject: Concept
    outcome: Concept
    provenance: List[Provenance] = Field(default_factory=list)


class NaturalConversion(Template):
    type: str = Field("NaturalConversion", const=True)
    subject: Concept
    outcome: Concept
    provenance: List[Provenance] = Field(default_factory=list)
