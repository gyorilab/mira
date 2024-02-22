"""This module provides functions to create a MIRA TemplateModel from a
Simple Interaction Format (SIF) file. The SIF format is a simple
space-delimited format where each line represents a relationship
between two entities. The first column is the source node, the second
column is the relation, and the third column is the target node. The
relation is a string that represents the type of interaction between
the source and target nodes. SIF files are useful as a minimal representation
of regulatory networks with positive/negative regulation."""

__all__ = ['template_model_from_sif_edges',
           'template_model_from_sif_file',
           'template_model_from_sif_url']

import requests
from mira.metamodel import *


def template_model_from_sif_edges(edges):
    """Return TemplateModel from a list of SIF edges.

    Parameters
    ----------
    edges : list
        A list of tuples of the form (source, rel, target) where source and
        target are strings representing the source and target nodes and rel
        is a string representing the relation between them.

    Returns
    -------
    TemplateModel
        A MIRA TemplateModel.
    """
    templates = []
    for source, rel, target in edges:
        source_concept = Concept(name=source)
        target_concept = Concept(name=target)
        if rel == 'POSITIVE':
            if source == target:
                t = NaturalReplication(subject=source_concept)
            else:
                t = ControlledReplication(
                        controller=source_concept,
                        subject=target_concept)
        elif rel == 'NEGATIVE':
            if source == target:
                t = NaturalDegradation(subject=source_concept)
            else:
                t = ControlledDegradation(
                        controller=source_concept,
                        subject=target_concept)
        templates.append(t)
    tm = TemplateModel(templates=templates)
    return tm


def template_model_from_sif_file(fname):
    """Return TemplateModel from a SIF file.

    Parameters
    ----------
    fname : str
        The path to the SIF file.

    Returns
    -------
    TemplateModel
        A MIRA TemplateModel.
    """
    with open(fname, 'r') as fh:
        edges = [line.strip().split()
                 for line in fh.readlines()
                 if line and not line.startswith('#')]
    return template_model_from_sif_edges(edges)


def template_model_from_sif_url(url):
    """Return TemplateModel from a SIF URL.

    Parameters
    ----------
    url : str
        The URL to the SIF file.

    Returns
    -------
    TemplateModel
        A MIRA TemplateModel.
    """
    res = requests.get(url)
    res.raise_for_status()
    edges = [line.strip().split()
             for line in res.text.split('\n')
             if line and not line.startswith('#')]
    return template_model_from_sif_edges(edges)
