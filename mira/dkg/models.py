"""Configuration for the DKG."""

from typing import Any, Mapping

from bioregistry import Collection, Resource
from mira.pydantic_setup import BaseModel
from pydantic import Field
from typing_extensions import Literal

__all__ = [
    "EntityType",
    "Config",
    "Xref",
    "Synonym",
]

EntityType = Literal["class", "property", "individual", "unknown"]


class Config(BaseModel):
    """Configuration for a custom metaregistry instance."""

    web: Mapping[str, Any] = Field(
        default_factory=dict,
        description="Configuration for the web application",
    )
    registry: Mapping[str, Resource] = Field(
        default_factory=dict, description="Custom registry entries"
    )
    collections: Mapping[str, Collection] = Field(
        default_factory=dict, description="Custom collections"
    )


class Xref(BaseModel):
    """Represents a typed cross-reference."""

    id: str = Field(description="The CURIE of the cross reference")
    type: str = Field(
        description="The CURIE for the cross reference predicate",
        example="skos:exactMatch",
    )


class Synonym(BaseModel):
    """Represents a typed synonym."""

    value: str = Field(description="The text of the synonym")
    type: str = Field(
        description="The CURIE for the synonym predicate",
        example="skos:exactMatch",
    )
