__all__ = ['find_models_with_grounding']

from typing import Mapping

from .template_model import TemplateModel, model_has_grounding


def find_models_with_grounding(template_models: Mapping[str, TemplateModel],
                               prefix: str, identifier: str) -> Mapping[str, TemplateModel]:
    """Filter a dict of models to ones containing a given grounding in any role."""
    return {k: m for k, m in template_models.items()
            if model_has_grounding(m, prefix, identifier)}
