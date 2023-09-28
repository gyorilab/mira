__all__ = ['template_model_from_petri_json']
import ast
import json
import sympy
from collections import defaultdict
from mira.metamodel import *


def template_model_from_petri_json_file(petri_json_file) -> TemplateModel:
    """Return a TemplateModel by processing a Petri net JSON file

    Parameters
    ----------
    petri_json_file : str
        A Petri net JSON file.

    Returns
    -------
    :
        A TemplateModel extracted from the Petri net.

    """
    with open(petri_json_file) as f:
        petri_json = json.load(f)
    return template_model_from_petri_json(petri_json)


def template_model_from_petri_json(petri_json) -> TemplateModel:
    """Return a TemplateModel by processing a Petri net JSON dict

    Parameters
    ----------
    petri_json : dict
        A Petri net JSON structure.

    Returns
    -------
    :
        A TemplateModel extracted from the Petri net.

    """
    # Extract concepts from states
    concepts = [state_to_concept(state) for state in petri_json['S']]
    initials = {concept.name: Initial(concept=concept,
                                      expression=SympyExprStr(sympy.Float(state.get('concentration'))))
                for state, concept in zip(petri_json['S'], concepts)
                if state.get('concentration') is not None}

    # Build lookups for inputs and outputs by transition index
    input_lookup = defaultdict(list)
    for input in petri_json['I']:
        input_lookup[input['it']].append(input['is'])
    output_lookup = defaultdict(list)
    for output in petri_json['O']:
        output_lookup[output['ot']].append(output['os'])

    # Now iterate over all the transitions and build templates
    templates = []
    parameters = {}
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
        # We can now get the appropriate concepts for each group
        input_concepts = [concepts[i - 1] for i in inputs]
        output_concepts = [concepts[i - 1] for i in outputs]
        controller_concepts = [concepts[i - 1] for i in controllers]
        # More than one template is possible in principle
        templates_from_transition = \
            list(transition_to_templates(transition, input_concepts,
                                         output_concepts,
                                         controller_concepts))
        templates_from_transition = list(templates_from_transition)
        # Get the parameters if any
        pv = transition.get('rate')
        pn = transition.get('tprop', {}).get('parameter_name')
        if pv is not None and pn is not None:
            parameters[pn] = Parameter(name=pn, value=pv)
            for template in templates_from_transition:
                template.set_mass_action_rate_law(pn)
        for template in templates_from_transition:
            templates.append(template)

    return TemplateModel(templates=templates, initials=initials,
                         parameters=parameters)


def state_to_concept(state):
    """Return a Concept from a Petri net state.

    Parameters
    ----------
    state : dict
        A Petri net state.

    Returns
    -------
    :
        A Concept extracted from the Petri net state.
    """
    # Example: 'mira_ids': "[('identity', 'ido:0000514')]"
    props = state.get('sprop', {})
    mira_ids = props.get('mira_ids')
    if mira_ids:
        mira_ids = ast.literal_eval(mira_ids)
        identifiers = dict([mira_ids[0][1].split(':', 1)])
    else:
        identifiers = {}
    # Example: 'mira_context': "[('city', 'geonames:5128581')]"
    mira_context = props.get('mira_context')
    if mira_context:
        context = dict(ast.literal_eval(props['mira_context']))
    else:
        context = {}
    return Concept(name=stringify_sname(state['sname']),
                   identifiers=identifiers,
                   context=context,
                   initial_value=state.get('concentration'))


def stringify_sname(sname):
    if isinstance(sname, str):
        return sname
    else:
        return '_'.join([stringify_sname(s) for s in sname])


def transition_to_templates(transition, input_concepts, output_concepts,
                            controller_concepts):
    p = transition.get('parameter_name')
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
            return []
        if len(controller_concepts) == 1:
            yield ControlledConversion(controller=controller_concepts[0],
                                       subject=input_concepts[0],
                                       outcome=output_concepts[0])
        else:
            yield GroupedControlledConversion(controllers=controller_concepts,
                                              subject=input_concepts[0],
                                              outcome=output_concepts[0])