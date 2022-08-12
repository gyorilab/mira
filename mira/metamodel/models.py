"""
Data models for metamodel templates.

Regenerate the JSON schema by running ``python -m mira.metamodel.models``.
"""
__all__ = ["Concept", "Template", "Provenance", "ControlledConversion", "NaturalConversion"]

import json
import sys
from pathlib import Path
from typing import List, Mapping

import pydantic
from pydantic import BaseModel, Field

HERE = Path(__file__).parent.resolve()
SCHEMA_PATH = HERE.joinpath("schema.json")


class Concept(BaseModel):
    name: str = Field(..., description="The name of the concept.")
    identifiers: Mapping[str, str] = Field(default_factory=dict, description="A mapping of namespaces to identifiers.")
    context: Mapping[str, str] = Field(default_factory=dict, description="A mapping of context keys to values.")


class Template(BaseModel):
    @classmethod
    def from_json(cls, data) -> "Template":
        template_type = data.pop("type")
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


def get_json_schema():
    """Get the JSON schema for MIRA."""
    rv = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://raw.githubusercontent.com/indralab/mira/main/mira/metamodel/schema.json",
    }
    rv.update(
        pydantic.schema.schema(
            [Concept, Template, NaturalConversion, ControlledConversion],
            title="MIRA Metamodel Template Schema",
            description="MIRA metamodel templates give a high-level abstraction of modeling appropriate for many domains.",
        )
    )
    return rv


def main():
    """Generate the JSON schema file."""
    schema = get_json_schema()
    SCHEMA_PATH.write_text(json.dumps(schema, indent=2))


if __name__ == "__main__":
    main()
