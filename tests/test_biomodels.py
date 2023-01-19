import os
import glob
import unittest

import tqdm
import pystow

from mira.metamodel.ops import simplify_rate_laws
from mira.modeling import Model
from mira.modeling.petri import PetriNetModel
from mira.sources.sbml import template_model_from_sbml_file


@unittest.skipIf(os.environ.get('GITHUB_ACTIONS') is not None,
                 reason="Meant to be run locally")
def test_process_biomodels():
    base_folder = pystow.join('mira', 'biomodels', 'models')
    fnames = glob.glob(os.path.join(base_folder.as_posix(),
                                    'BIOMD*/BIOMD*.xml'))
    for fname in tqdm.tqdm(fnames):
        tm_old = template_model_from_sbml_file(fname)
        old_template_count = len(tm_old.templates)
        tm = simplify_rate_laws(tm_old)
        new_template_count = len(tm.templates)
        if old_template_count != new_template_count:
            breakpoint()
        model = Model(tm)
        petri = PetriNetModel(model)
        pj = petri.to_json()
        assert pj
        assert tm.templates

