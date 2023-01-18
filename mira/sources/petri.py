import ast
from collections import defaultdict
from mira.metamodel import *


def template_model_from_petri_json(petri_json):
    concepts = [state_to_concept(state) for state in petri_json['S']]
    input_lookup = defaultdict(list)
    for input in petri_json['I']:
        input_lookup[input['it']].append(input['is'])
    output_lookup = defaultdict(list)
    for output in petri_json['O']:
        output_lookup[output['ot']].append(output['os'])

    templates = []
    for idx, transition in enumerate(petri_json.get('T', []), start=1):
        inputs = input_lookup[idx]
        outputs = output_lookup[idx]
        # Since inputs and outputs can contain the same state multiple times
        # and in general we want to preserve the number of times a state
        # appears, we identify controllers one by one, and remove them
        # from the input/output lists
        controllers = []
        both = set(inputs) & set(outputs)
        while both:
            shared = next(iter(both))
            controllers.append(shared)
            inputs.remove(shared)
            outputs.remove(shared)
            both = set(inputs) & set(outputs)
        input_concepts = [concepts[i - 1] for i in inputs]
        output_concepts = [concepts[i - 1] for i in outputs]
        controller_concepts = [concepts[i - 1] for i in controllers]
        templates.extend(transition_to_templates(transition, input_concepts,
                                                 output_concepts,
                                                 controller_concepts))
    return TemplateModel(templates=templates)

def state_to_concept(state):
    # Example: 'mira_ids': "[('identity', 'ido:0000514')]"
    mira_ids = ast.literal_eval(state['mira_ids'])
    if mira_ids:
        identifiers = dict([mira_ids[0][1].split(':', 1)])
    else:
        identifiers = {}
    # Example: 'mira_context': "[('city', 'geonames:5128581')]"
    context = dict(ast.literal_eval(state['mira_context']))
    return Concept(name=state['sname'],
                   identifiers=identifiers,
                   context=context,
                   initial_value=state.get('mira_initial_value'))


def transition_to_templates(transition, input_concepts, output_concepts,
                            controller_concepts):
    p = transition.get('parameter_value')
    if not controller_concepts:
        if not input_concepts:
            for output_concept in output_concepts:
                yield NaturalProduction(outcome=output_concept)
        elif not output_concepts:
            for input_concept in input_concepts:
                yield NaturalDegradation(subject=input_concept)
        else:
            for input_concept in input_concepts:
                for output_concept in output_concepts:
                    yield NaturalConversion(subject=input_concept,
                                            outcome=output_concept)
    else:
        if not (len(input_concepts) == 1 and len(output_concepts) == 1):
            return
        if len(controller_concepts) == 1:
            yield ControlledConversion(controller=controller_concepts[0],
                                       subject=input_concepts[0],
                                       outcome=output_concepts[0])
        else:
            yield GroupedControlledConversion(controllers=controller_concepts,
                                              subject=input_concepts[0],
                                              outcome=output_concepts[0])