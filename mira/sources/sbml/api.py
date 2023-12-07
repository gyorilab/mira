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
    """Extract a MIRA template model from a file containing SBML XML.

    Parameters
    ----------
    file_path :
        The path to the SBML file.
    model_id :
        The ID of the model to extract. (Optional) If not provided, an attempt
        will be made to extract an ID from the SBML file if it's a BIOMODELS
        model.
    reporter_ids :
        An iterable of reporter IDs

    Returns
    -------
    :
        The extracted MIRA template model.
    """
    sbml_model = sbml_model_from_file(file_path)
    return template_model_from_sbml_model(sbml_model, model_id=model_id,
                                          reporter_ids=reporter_ids)


def template_model_from_sbml_file_obj(
        file,
        *,
        model_id: Optional[str] = None,
        reporter_ids: Optional[Iterable[str]] = None,
) -> TemplateModel:
    """Extract a MIRA template model from a file object containing SBML XML.

    Parameters
    ----------
    file :
        The open file object containing the SBML XML.
    model_id :
        The ID of the model to extract. (Optional) If not provided, an attempt
        will be made to extract an ID from the SBML file if it's a BIOMODELS
        model.
    reporter_ids :
        An iterable of reporter IDs

    Returns
    -------
    :
        The extracted MIRA template model.
    """
    return template_model_from_sbml_string(
        file.read().decode("utf-8"), model_id=model_id, reporter_ids=reporter_ids
    )


def sbml_model_from_file(fname):
    """Return an SBML model object from an SBML file.

    Parameters
    ----------
    fname :
        The path to the SBML file.

    Returns
    -------
    :
        An SBML model object.
    """
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
    """Extract a MIRA template model from a string representing SBML XML.

    Parameters
    ----------
    s :
        The string containing the SBML XML.
    model_id :
        The ID of the model to extract. (Optional) If not provided, an attempt
        will be made to extract an ID from the SBML xml if it's a BIOMODELS
        model.
    reporter_ids :
        An iterable of reporter IDs

    Returns
    -------
    :
        The extracted TemplateModel.
    """
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
    """Extract a MIRA template model from an SBML model object.

    Parameters
    ----------
    sbml_model :
        The SBML model object.
    model_id :
        The ID of the model to extract. (Optional) If not provided, an attempt
        will be made to extract an ID from the SBML model if it's a BIOMODELS
        model.

    Returns
    -------
    :
        The extracted TemplateModel.
    """
    processor = SbmlProcessor(sbml_model, model_id=model_id,
                              reporter_ids=reporter_ids)
    tm = processor.extract_model()
    return tm
