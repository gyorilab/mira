__all__ = [
    "compose",
]

from mira.metamodel import *


class AuthorWrapper:
    """
    Wrapper around the Author class that allows for Author object comparison
    based on the "name" attribute of the Author object such that when
    annotations are merged between two template models, Author names won't
    be duplicated if the two template models being composed share an author.
    """

    def __init__(self, author: Author):
        self.author = author

    def __hash__(self):
        return hash(self.author.name)

    def __eq__(self, other):
        if isinstance(other, AuthorWrapper):
            return self.author.name == other.author.name
        return False


def compose(tm_list):
    """
    Compose a list of template models into a single template model

    Parameters
    ----------
    tm_list :
        The list of template models to compose

    Returns
    -------
    :
        The composed template model derived from the list of template models
    """
    if len(tm_list) < 2:
        raise ValueError(f"Expected the list of template models to be at "
                         f"least length 2.")

    intermediate_results = [_compose_two_tms(tm_list[0], tm_list[1])]

    for intermediate_index, tm in enumerate(tm_list[2:]):
        intermediate_results.append(_compose_two_tms(
            intermediate_results[intermediate_index], tm)
        )

    return intermediate_results[-1]


def _compose_two_tms(tm0, tm1):
    """
    Helper method that composes two template models into one

    Parameters
    ----------
    tm0 :
        The first template model to be composed
    tm1 :
        The second template model to be composed

    Returns
    -------
    :
        The composed template model
    """
    # what would rate law conflict look like, and where would it appear
    # Would it appear in the case that the similarity score is 1.0 between
    # two template models but the corresponding templates from the two
    # models have a different rate-laws?
    # Do we define model priority order by the specificity of the concepts
    # in the templates in question? Or can it be a user-defined parameter?
    model_list = [tm0, tm1]
    rf_func = get_dkg_refinement_closure().is_ontological_child
    compare = TemplateModelComparison(model_list,
                                      refinement_func=rf_func)
    comparison_result = compare.model_comparison.get_similarity_scores()

    if comparison_result[0]["score"] == 0:
        # get the union of all template model attributes
        # as the models are 100% distinct
        new_templates = tm0.templates + tm1.templates
        new_parameters = {**tm0.parameters, **tm1.parameters}
        new_initials = {**tm0.initials, **tm1.initials}
        new_observables = {**tm0.observables, **tm1.observables}
        new_annotations = annotation_composition(tm0.annotations,
                                                 tm1.annotations)

        return TemplateModel(templates=new_templates,
                             parameters=new_parameters,
                             initials=new_initials,
                             observables=new_observables,
                             annotations=new_annotations)

    elif comparison_result[0]['score'] == 1.0:
        # return the first template model as both
        # template models are exactly the same
        return tm0
    else:
        # template models are partially similar
        new_templates = []
        new_parameters = {}
        new_initials = {}
        new_observables = {}
        new_annotations = annotation_composition(tm0.annotations,
                                                 tm1.annotations)

        # TODO: Verify if pairwise comparison with all templates from both
        #  template models is the correct way to proceed? Would we want to
        #  use zip_longest and pad shorter template list? Using zip_longest
        #  means template list order matters.
        for outer_template in tm0.templates:
            for inner_template in tm1.templates:
                if inner_template.refinement_of(outer_template,
                                                refinement_func=rf_func):
                    # inner_template from tm1 is a more specific version
                    # of outer_template from tm0

                    # Don't want to add a template that has already been added
                    if inner_template not in new_templates:
                        new_templates.append(inner_template)
                        process_template(inner_template, tm1, new_parameters,
                                         new_initials,
                                         new_observables)

                elif outer_template.refinement_of(inner_template,
                                                  refinement_func=rf_func):
                    # outer_template from tm0 is a more specific version
                    # of inner_template from tm1
                    if outer_template not in new_templates:
                        new_templates.append(outer_template)
                        process_template(outer_template, tm0, new_parameters,
                                         new_initials,
                                         new_observables)

                else:
                    # the two templates are disjoint
                    if outer_template not in new_templates:
                        new_templates.append(outer_template)
                        process_template(outer_template, tm0, new_parameters,
                                         new_initials,
                                         new_observables)

                    if inner_template not in new_templates:
                        new_templates.append(inner_template)
                        process_template(inner_template, tm1, new_parameters,
                                         new_initials,
                                         new_observables)

        return TemplateModel(templates=new_templates,
                             parameters=new_parameters,
                             initials=new_initials,
                             observables=new_observables,
                             annotations=new_annotations)


def process_template(added_template, tm, parameters, initials, observables):
    """
    Helper method that updates the dictionaries that contain the attributes
    to be used for the new composed template model

    Parameters
    ----------
    added_template :
        The template that was added to the list of templates for the composed
        template model
    tm :
        The input template model to the model_compose method that contains the
        template to be added
    parameters :
        The dictionary of parameters to update that will be used for the
        composed template model
    initials :
        The dictionary of initials to update that will be used for the
        composed template model
    observables :
        The dictionary observables to update that will be used for the
        composed template model

    """
    parameters.update({param_name: tm.parameters[param_name] for param_name
                       in added_template.get_parameter_names()})
    initials.update({initial_name: tm.initials[initial_name] for
                     initial_name in added_template.get_concept_names()
                     if initial_name in tm.initials})


def update_observables():
    # TODO: Clarify on how to update observables for template models
    #  that are partially similar
    pass


def annotation_composition(tm0_annot, tm1_annot):
    """
    Helper method that combines the annotations of the models being composed

    Parameters
    ----------
    tm0_annot :
        Annotations of the first template model
    tm1_annot :
        Annotations of the second template model

    Returns
    -------
    :
        The created `Annotations` object from combining the input template 
        model annotations
    """

    if tm0_annot is None:
        return tm1_annot
    elif tm1_annot is None:
        return tm0_annot
    elif tm0_annot is None and tm1_annot is None:
        return None

    new_name = f"{tm0_annot.name} + {tm1_annot.name}"
    new_description = (
        f"First Template Model Description: {tm0_annot.description}"
        f"\nSecond Template Model Description: {tm1_annot.description}")
    new_license = (f"First Template Model License: {tm0_annot.license}"
                   f"\nSecond Template Model License: {tm1_annot.license}")

    # Use the AuthorWrapper class here to create a list of Author
    # objects with unique name attributes
    new_authors = tm0_annot.authors + tm1_annot.authors
    new_authors = set(AuthorWrapper(author) for author in new_authors)
    new_authors = [wrapper.author for wrapper in new_authors]

    new_references = list(
        set(tm0_annot.references) | set(tm1_annot.references))
    new_locations = list(
        set(tm0_annot.locations) | set(tm1_annot.locations))
    new_pathogens = list(
        set(tm0_annot.pathogens) | set(tm1_annot.pathogens))
    new_diseases = list(
        set(tm0_annot.diseases) | set(tm1_annot.diseases))
    new_hosts = list(set(tm0_annot.hosts) | set(tm1_annot.hosts))
    new_model_types = list(
        set(tm0_annot.model_types) | set(tm1_annot.model_types))

    # How to handle time related attributes of Annotations
    # which time_scale to use?
    # set rule for determining time_start and time_end
    # (e.g. always choose earlier time_start and later time_end)?
    return Annotations(name=new_name, description=new_description,
                       license=new_license, authors=new_authors,
                       references=new_references, locations=new_locations,
                       pathogens=new_pathogens, dieases=new_diseases,
                       hosts=new_hosts, model_types=new_model_types)
