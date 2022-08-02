from typing import List

from pydantic import BaseModel

from mira.metamodel import Template


class Model(BaseModel):
    templates: List[Template]
