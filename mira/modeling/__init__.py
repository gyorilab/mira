from typing import List

from pydantic import BaseModel

from mira.metamodel import Template


class TemplateModel(BaseModel):
    templates: List[Template]

    @classmethod
    def from_json(cls, data) -> "Model":
        templates = [Template.from_json(template) for template in data["templates"]]
        return cls(templates=templates)
