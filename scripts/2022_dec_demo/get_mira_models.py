import csv
import json
from collections import defaultdict
import pandas
from mira.metamodel import model_to_json_file
from mira.sources.bilayer import template_model_from_bilayer_file
from mira.modeling import Model
from mira.modeling.acsets.petri import PetriNetModel


model_names = [
    'CHIME_SIR_dynamics_BiLayer',
    'CHIME_SVIIvR_dynamics_BiLayer',
    'Bucky_SEIIIRRD_BiLayer'
]


def dump_initial_symbol_list(fname):
    var_names = defaultdict(list)
    param_names = defaultdict(list)
    for model_name in model_names:
        with open(model_name + '.json', 'r') as fh:
            bilayer = json.load(fh)
            for var in bilayer['Qin']:
                var_names[model_name].append(var['variable'])
            for box in bilayer['Box']:
                param_names[model_name].append(box['parameter'])
    rows = []
    for model_name in model_names:
        for var_name in var_names[model_name]:
            rows.append([model_name, var_name, 'state'])
        for param_name in param_names[model_name]:
            rows.append([model_name, param_name, 'parameter'])
    with open(fname, 'w') as fh:
        writer = csv.writer(fh)
        writer.writerows(rows)


context_mappings = {
    'Context: Disease Status (ncit:C27992)': 'disease_severity',
    'Context: Vaccination Status': 'vaccination_status',
    'Context: Hospitalization': 'hospitalization_status'
}


def fetch_symbol_grounding():
    url = 'https://docs.google.com/spreadsheets/' \
          'd/1ZCPGkfAgOf81MUTT9dIDlrH8lmEM8lKfYoBWiAL5S2s/' \
          'export?format=csv&gid=520545206'
    df = pandas.read_csv(url)
    parameters = {m: {} for m in model_names}
    concepts = {m: {} for m in model_names}
    for _, row in df.iterrows():
        model = row['Model']
        if row['Type'] == 'state':
            concepts[model][row['Symbol']] = {'identity': row['Identity']}
            for context_col, mapped_col in context_mappings.items():
                if not pandas.isna(row[context_col]):
                    concepts[model][row['Symbol']][mapped_col] = row[context_col]
        else:
            parameters[model][row['Symbol']] = {
                'identity': row['Identity']
            }
            for context_col, mapped_col in context_mappings.items():
                if not pandas.isna(row[context_col]):
                    parameters[model][row['Symbol']][mapped_col] = row[context_col]
    return concepts, parameters


if __name__ == '__main__':
    template_models = {}
    for model_name in model_names:
        template_models[model_name] = \
            template_model_from_bilayer_file(model_name + '.json')
    #dump_initial_symbol_list('model_grounding.csv')
    concepts, parameters = fetch_symbol_grounding()
    for model_name, template_model in template_models.items():
        for parameter, data in parameters[model_name].items():
            template_model.parameters[parameter].identifiers = \
                dict([data['identity'].split(':')])
            for context_key in context_mappings.values():
                if context_key in data:
                    template_model.parameters[parameter].context[context_key] = \
                        data[context_key]
        for concept, data in concepts[model_name].items():
            for template in template_model.templates:
                for model_concept in template.get_concepts():
                    if model_concept.name == concept:
                        model_concept.identifiers = \
                            dict([data['identity'].split(':')])
                        for context_key in context_mappings.values():
                            if context_key in data:
                                model_concept.context[context_key] = \
                                    data[context_key]
        pm = PetriNetModel(Model(template_model))
        pm.to_json_file(model_name + '_petri.json')

        model_to_json_file(template_model, model_name + '_mira.json')