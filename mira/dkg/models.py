"""Configuration for the DKG."""

from bioregistry import Collection, Resource
from typing import Any, Mapping

from pydantic import BaseModel, Field

__all__ = [
    "Config",
]


class Config(BaseModel):
    """Configuration for a custom metaregistry instance."""

    web: Mapping[str, Any] = Field(
        default_factory=dict, description="Configuration for the web application"
    )
    registry: Mapping[str, Resource] = Field(
        default_factory=dict, description="Custom registry entries"
    )
    collections: Mapping[str, Collection] = Field(
        default_factory=dict, description="Custom collections"
    )
