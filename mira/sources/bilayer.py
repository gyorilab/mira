"""This module implements an input processor for bilayer representations
of models based on mass-action kinetics.

:: code

    {"Wa":[{"influx":1,"infusion":2},
                 {"influx":2,"infusion":3}],
     "Win":[{"arg":1,"call":1},
                    {"arg":2,"call":1},
                    {"arg":2,"call":2}],
     "Box":[{"parameter":"beta"},
                    {"parameter":"gamma"}],
     "Qin":[{"variable":"S"},
                    {"variable":"I"},
                    {"variable":"R"}],
     "Qout":[{"tanvar":"S'"},
                     {"tanvar":"I'"},
                     {"tanvar":"R'"}],
     "Wn":[{"efflux":1,"effusion":1},
                 {"efflux":2,"effusion":2}]}
"""
import json
from mira.metamodel.templates import *


def box_to_template(box):
    # Assert assumptions in template patterns
    assert len(box['inputs']) <= 1
    assert len(box['outputs']) <= 1
    # Unpack inputs and outputs
    input = box['inputs'][0] if box['inputs'] else None
    output = box['outputs'][0] if box['outputs'] else None
    # Decide on template class based on number of controllers
    if not box['controllers']:
        if not input:
            return NaturalProduction(outcome=output)
        elif not output:
            return NaturalDegradation(subject=input)
        else:
            return NaturalConversion(subject=input, outcome=output)
    elif len(box['controllers']) == 1:
        return ControlledConversion(controller=box['controllers'][0],
                                    subject=input, outcome=output)
    else:
        return GroupedControlledConversion(controllers=box['controllers'],
                                           subject=input, outcome=output)


def template_model_from_bilayer_file(fname):
    with open(fname, 'r') as fh:
        return template_model_from_bilayer(json.load(fname))


def template_model_from_bilayer(bilayer_json):
    # For each box
    concepts = {idx + 1: Concept(name=q['variable'])
                for idx, q in enumerate(bilayer_json['Qin'])}
    boxes = [{'inputs': [], 'outputs': [], 'controllers': []}
             for _ in range(len(bilayer_json['Box']))]
    for consumption in bilayer_json['Wn']:
        boxes[consumption['efflux'] - 1]['inputs'].append(
            concepts[consumption['effusion']])
    for production in bilayer_json['Wa']:
        boxes[production['influx'] - 1]['outputs'].append(
            concepts[production['infusion']])
    for control in bilayer_json['Win']:
        if concepts[control['arg']] not in boxes[control['call'] - 1]['inputs']:
            boxes[control['call'] - 1]['controllers'].append(
                concepts[control['arg']])

    templates = []
    for box in boxes:
        templates.append(box_to_template(box))
    return TemplateModel(templates=templates)