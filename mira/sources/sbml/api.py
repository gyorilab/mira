from typing import Iterable, Optional

from libsbml import SBMLReader

from mira.metamodel import TemplateModel
from .processor import SbmlProcessor


__all__ = [
    "template_model_from_sbml_file",
    "template_model_from_sbml_file_obj",
    "template_model_from_sbml_string",
    "template_model_from_sbml_model",
    "sbml_model_from_file"
]


def template_model_from_sbml_file(
        file_path,
        *,
        model_id: Optional[str] = None,
        reporter_ids: Optional[Iterable[str]] = None,
) -> TemplateModel:
    """Extract a MIRA template model from a file containing SBML XML."""
    sbml_model = sbml_model_from_file(file_path)
    return template_model_from_sbml_model(sbml_model, model_id=model_id,
                                          reporter_ids=reporter_ids)


def template_model_from_sbml_file_obj(
        file,
        *,
        model_id: Optional[str] = None,
        reporter_ids: Optional[Iterable[str]] = None,
) -> TemplateModel:
    """Extract a MIRA template model from a file object containing SBML XML."""
    return template_model_from_sbml_string(
        file.read().decode("utf-8"), model_id=model_id, reporter_ids=reporter_ids
    )


def sbml_model_from_file(fname):
    """Return an SBML model object from an SBML file."""
    with open(fname, 'rb') as fh:
        sbml_string = fh.read().decode('utf-8')
    sbml_document = SBMLReader().readSBMLFromString(sbml_string)
    return sbml_document.getModel()


def template_model_from_sbml_string(
        s: str,
        *,
        model_id: Optional[str] = None,
        reporter_ids: Optional[Iterable[str]] = None,
) -> TemplateModel:
    """Extract a MIRA template model from a string representing SBML XML."""
    sbml_document = SBMLReader().readSBMLFromString(s)
    return template_model_from_sbml_model(
        sbml_document.getModel(), model_id=model_id, reporter_ids=reporter_ids
    )


def template_model_from_sbml_model(
        sbml_model,
        *,
        model_id: Optional[str] = None,
        reporter_ids: Optional[Iterable[str]] = None,
) -> TemplateModel:
    """Extract a MIRA template model from an SBML model object."""
    processor = SbmlProcessor(sbml_model, model_id=model_id,
                              reporter_ids=reporter_ids)
    tm = processor.extract_model()
    return tm
