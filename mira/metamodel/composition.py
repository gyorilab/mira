__all__ = [
    "model_compose"
]

from mira.examples.sir import sir, sir_2_city
import requests
import sympy
from mira.metamodel import *
from mira.sources.amr import model_from_url
from mira.sources.amr import petrinet
from mira.sources.amr import regnet
from mira.sources.amr import stockflow
from mira.modeling.amr.regnet import template_model_to_regnet_json
from mira.metamodel.comparison import ModelComparisonGraphdata, TemplateModelComparison
from mira.metamodel.comparison import RefinementClosure, \
    get_dkg_refinement_closure
from mira.metamodel.template_model import *

petrinet_example = 'https://raw.githubusercontent.com/DARPA-ASKEM/' \
                   'Model-Representations/main/petrinet/examples/sir.json'
regnet_example = 'https://raw.githubusercontent.com/DARPA-ASKEM/' \
                 'Model-Representations/main/regnet/examples/lotka_volterra.json'


class AuthorWrapper:
    def __init__(self, author: Author):
        self.author = author

    def __hash__(self):
        return hash(self.author.name)

    def __eq__(self, other):
        if isinstance(other, AuthorWrapper):
            return self.author.name == other.author.name
        return False


def model_compose(tm0, tm1):
    model_list = [tm0, tm1]
    rc = get_dkg_refinement_closure()
    compare = TemplateModelComparison(model_list, refinement_func=rc.is_ontological_child)
    comparison_result = compare.model_comparison.get_similarity_scores()

    if comparison_result[0]["score"] == 0:
        # get the union of all template model attributes
        new_templates = tm0.templates + tm1.templates
        new_parameters = {**tm0.parameters, **tm1.parameters}
        new_initials = {**tm0.initials, **tm1.initials}
        new_observables = {**tm0.observables, **tm1.observables}
        new_annotations = annotation_composition(tm0.annotations, tm1.annotations)

        new_tm = TemplateModel(templates=new_templates, parameters=new_parameters,
                               initials=new_initials, observables=new_observables,
                               annotations=new_annotations)

        return new_tm
    else:
        for template in tm0:
            pass
    pass


def parameter_composition():
    pass


def initial_composition():
    pass


def annotation_composition(tm0_annotations, tm1_annotations):
    new_name = f"{tm0_annotations.name} + {tm1_annotations.name}"
    new_description = (f"First Template Model Description: {tm0_annotations.description}"
                       f"\nSecond Template Model Description: {tm1_annotations.description}")
    new_license = (f"First Template Model License: {tm0_annotations.license}"
                   f"\nSecond Template Model License: {tm1_annotations.license}")

    new_authors = tm0_annotations.authors + tm1_annotations.authors
    new_authors = set(AuthorWrapper(author) for author in new_authors)
    new_authors = [wrapper.author for wrapper in new_authors]

    new_references = list(set(tm0_annotations.references) | set(tm1_annotations.references))
    new_locations = list(set(tm0_annotations.locations) | set(tm1_annotations.locations))
    new_pathogens = list(set(tm0_annotations.pathogens) | set(tm1_annotations.pathogens))
    new_diseases = list(set(tm0_annotations.diseases) | set(tm1_annotations.diseases))
    new_hosts = list(set(tm0_annotations.hosts) | set(tm1_annotations.hosts))
    new_model_types = list(set(tm0_annotations.model_types) | set(tm1_annotations.model_types))

    return Annotations(name=new_name, description=new_description,
                       license=new_license, authors=new_authors,
                       references=new_references, locations=new_locations,
                       pathogens=new_pathogens, dieases=new_diseases,
                       hosts=new_hosts, model_types=new_model_types)


if __name__ == "__main__":
    # test
    tm0 = model_from_url(petrinet_example)
    tm1 = model_from_url(regnet_example)
    new_tm = model_compose(tm0, tm1)
    pass
