"""Rebuild with ``python -m mira.metamodel.schema``."""

__all__ = ["get_json_schema", "SCHEMA_PATH"]

import json
from pathlib import Path

import pydantic
from pydantic import BaseModel, create_model
from pydantic.json_schema import model_json_schema

from . import Concept, Template, TemplateModel

HERE = Path(__file__).parent.resolve()
SCHEMA_PATH = HERE.joinpath("schema.json")


def get_json_schema():
    """Get the JSON schema for MIRA."""
    rv = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://raw.githubusercontent.com/indralab/mira/main/mira/metamodel/schema.json",
        "title": "MIRA Metamodel Template Schema",
        "description": "MIRA metamodel templates give a high-level abstraction of modeling appropriate for many domains.",
    }

    models = [Concept, Template, *Template.__subclasses__(), TemplateModel]

    CombinedModel = create_model(
        "CombinedModel",
        **{model.__name__: (model, ...) for model in models}
    )

    schema = model_json_schema(
        CombinedModel,
        mode='validation',
    )

    # Remove the top-level 'title' and 'description' from the generated schema
    schema.pop('title', None)
    schema.pop('description', None)

    rv.update(schema)
    return rv


def _encoder(x):
    if isinstance(x, BaseModel):
        return x.dict()
    return x


def main():
    """Generate the JSON schema file."""
    schema = get_json_schema()
    SCHEMA_PATH.write_text(json.dumps(schema, indent=2, default=_encoder))


if __name__ == "__main__":
    main()
