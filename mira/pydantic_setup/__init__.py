from pydantic import BaseModel as PydanticBaseModel, Extra


class BaseModel(PydanticBaseModel, extra=Extra.forbid):
    """Base class for all models."""
