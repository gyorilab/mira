"""This script traverses a folder for JSON-serialized MIRA Template Models
and finds all the groundings for Concepts used in the model. It then
puts a ranked list of these groundings (as CURIEs) in a resource file for
the purpose of DKG search ranking."""

import os
import sys
import glob
from collections import Counter

import bioregistry

from mira.dkg.resources import get_resource_path
from mira.metamodel import model_from_json_file


if __name__ == '__main__':
    base_folder = sys.argv[0] if len(sys.argv) > 1 else \
        os.path.join(os.path.expanduser('~'), '.data', 'mira', 'biomodels',
                     'models')

    # Collect all Concept identifiers from all models
    all_identifiers = []
    model_files = glob.glob(os.path.join(base_folder, '**', '*.json'))
    for model_file in model_files:
        try:
            model = model_from_json_file(model_file)
        except Exception as e:
            print('Could not process MIRA Template model from %s' % model_file)
        for template in model.templates:
            concepts = template.get_concepts()
            for concept in concepts:
                for k, v in concept.identifiers.items():
                    if k == 'biomodels.species':
                        continue
                    if not bioregistry.is_valid_identifier(k, v):
                        print(f'Invalid identifier in '
                              f'{os.path.basename(model_file)}: {k}:{v}')
                        continue
                    all_identifiers.append((k, v))

    # We now sort the identifiers based on frequency and secondarily
    # by just the ID itself to avoid non-deterministic ordering
    ranked_identifiers = sorted(Counter(all_identifiers).items(),
                                key=lambda x: (x[1], x[0]), reverse=True)

    # The list is written into a DKG resource file
    with open(get_resource_path('search_priority_list.txt'), 'w') as fh:
        fh.writelines(['%s:%s\n' % identifer
                       for identifer, _ in ranked_identifiers])
