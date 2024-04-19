from typing import Iterable, Optional

from libsbml import SBMLReader

from mira.metamodel import TemplateModel
from .qual_processor import SbmlQualProcessor

__all__ = [
    "template_model_from_sbml_qual_file",
    "template_model_from_sbml_qual_file_obj",
    "template_model_from_sbml_qual_string",
    "template_model_from_sbml_qual_model",
    "sbml_qual_model_from_file",
]


def template_model_from_sbml_qual_file(
    file_path,
    *,
    model_id: Optional[str] = None,
    reporter_ids: Optional[Iterable[str]] = None,
) -> TemplateModel:
    """Extract a MIRA template model from a file containing SBML Qual XML.

    Parameters
    ----------
    file_path :
        The path to the SBML Qual file.
    model_id :
        The ID of the model to extract. (Optional) If not provided, an attempt
        will be made to extract an ID from the SBML Qual file if it's a BIOMODELS
        model.
    reporter_ids :
        An iterable of reporter IDs

    Returns
    -------
    :
        The extracted MIRA template model.
    """
    sbml_model, qual_model = sbml_qual_model_from_file(file_path)
    return template_model_from_sbml_qual_model(
        sbml_model, qual_model, model_id=model_id, reporter_ids=reporter_ids
    )


def template_model_from_sbml_qual_file_obj(
    file,
    *,
    model_id: Optional[str] = None,
    reporter_ids: Optional[Iterable[str]] = None,
) -> TemplateModel:
    """Extract a MIRA template model from a file object containing SBML Qual XML.

    Parameters
    ----------
    file :
        The open file object containing the SBML Qual XML.
    model_id :
        The ID of the model to extract. (Optional) If not provided, an attempt
        will be made to extract an ID from the SBML Qual file if it's a BIOMODELS
        model.
    reporter_ids :
        An iterable of reporter IDs

    Returns
    -------
    :
        The extracted MIRA template model.
    """
    return template_model_from_sbml_qual_string(
        file.read().decode("utf-8"),
        model_id=model_id,
        reporter_ids=reporter_ids,
    )


def sbml_qual_model_from_file(fname):
    """Return an SBML model object and SBML Qual model object from an SBML Qual file.

    Parameters
    ----------
    fname :
        The path to the SBML Qual file.

    Returns
    -------
    :
        An SBML model object.
    :
        An SBMl Qual Model object.
    """
    with open(fname, "rb") as fh:
        sbml_string = fh.read().decode("utf-8")
    sbml_document = SBMLReader().readSBMLFromString(sbml_string)
    sbml_model = sbml_document.getModel()
    qual_model_plugin = sbml_model.getPlugin("qual")
    return sbml_model, qual_model_plugin


def template_model_from_sbml_qual_string(
    s: str,
    *,
    model_id: Optional[str] = None,
    reporter_ids: Optional[Iterable[str]] = None,
) -> TemplateModel:
    """Extract a MIRA template model from a string representing SBML Qual XML.

    Parameters
    ----------
    s :
        The string containing the SBML Qual XML.
    model_id :
        The ID of the model to extract. (Optional) If not provided, an attempt
        will be made to extract an ID from the SBML Qual xml if it's a BIOMODELS
        model.
    reporter_ids :
        An iterable of reporter IDs

    Returns
    -------
    :
        The extracted TemplateModel.
    """
    sbml_document = SBMLReader().readSBMLFromString(s)
    sbml_model = sbml_document.getModel()
    qual_model_plugin = sbml_model.getPlugin("qual")
    return template_model_from_sbml_qual_model(
        sbml_model,
        qual_model_plugin,
        model_id=model_id,
        reporter_ids=reporter_ids,
    )


def template_model_from_sbml_qual_model(
    sbml_model,
    qual_model,
    *,
    model_id: Optional[str] = None,
    reporter_ids: Optional[Iterable[str]] = None,
) -> TemplateModel:
    """Extract a MIRA template model from an SBML Qual model object.

    Parameters
    ----------
    sbml_model :
        The SBML model object.
    qual_model :
        The SBML Qual model object
    model_id :
        The ID of the model to extract. (Optional) If not provided, an attempt
        will be made to extract an ID from the SBML Qual model if it's a BIOMODELS
        model.

    Returns
    -------
    :
        The extracted TemplateModel.
    """
    processor = SbmlQualProcessor(
        sbml_model, qual_model, model_id=model_id, reporter_ids=reporter_ids
    )
    tm = processor.extract_model()
    return tm
