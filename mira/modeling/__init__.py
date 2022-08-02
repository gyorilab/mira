from typing import List

from pydantic import BaseModel

from mira.metamodel import Template, template_resolver


class Model(BaseModel):
    templates: List[Template]

    @classmethod
    def from_json(cls, data) -> "Model":
        templates = []
        for template_data in data["templates"]:
            name = template_data.pop("type")
            templates.append(template_resolver.make(name, template_data))
        return cls(templates=templates)
