"""Compose input template models into a single template model"""

__all__ = [
    "compose",
    "compose_two_models"
]

from copy import deepcopy
import sympy

from .comparison import TemplateModelComparison, default_dkg_refinement_closure
from .template_model import Annotations, TemplateModel


def compose(tm_list):
    """Compose a list of template models into a single template model

    This method composes two template models iteratively. For the initial
    composition of the first two template models in the list, this method
    prioritizes attributes (parameters, initials, templates,
    annotation time, model time, etc.) of the first template model in the
    list.

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
    composed_model = tm_list[0]
    for tm in tm_list[1:]:
        composed_model = compose_two_models(composed_model, tm)
    return composed_model


def compose_two_models(tm0, tm1):
    """Compose two template models into one

    The method prioritizes attributes (parameters, initials, templates,
    annotation time, model time, etc.) of the first template model passed in.

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
    model_list = [tm0, tm1]
    rf_func = default_dkg_refinement_closure.is_ontological_child
    compare = TemplateModelComparison(model_list,
                                      refinement_func=rf_func)
    compare_graph = compare.model_comparison
    comparison_result = compare_graph.get_similarity_scores()
    tm_keys = [tm_key for tm_key in compare_graph.template_models]
    outer_tm_id = tm_keys[0]
    inner_tm_id = tm_keys[1]

    # Create a copy of observables in case we need to modify observable
    # expressions
    new_observables = {key: deepcopy(value) for d in (tm1.observables,
                                                      tm0.observables)
                       for key, value in d.items()}

    # Create a copy of templates in case we need to modify template rate laws
    # when doing time substitutions
    tm0.templates = deepcopy(tm0.templates)
    tm1.templates = deepcopy(tm1.templates)

    new_annotations = annotation_composition(tm0.annotations,
                                             tm1.annotations)

    # prioritize tm0 time
    new_time = tm0.time if tm0.time else tm1.time

    if comparison_result[0]["score"] == 0:
        # get the union of all template model attributes
        # as the models are 100% distinct
        # prioritize tm0
        new_templates = tm0.templates + tm1.templates
        new_parameters = {**tm1.parameters, **tm0.parameters}
        new_initials = {**tm1.initials, **tm0.initials}

        composed_tm = TemplateModel(templates=new_templates,
                                    parameters=new_parameters,
                                    initials=new_initials,
                                    observables=new_observables,
                                    annotations=new_annotations,
                                    time=new_time)

        if tm0.time and tm1.time:
            substitute_time(composed_tm, tm0.time, tm1.time)
        return composed_tm
    else:
        # template models are not 100% disjoint
        new_templates = []
        new_parameters = {}
        new_initials = {}
        concept_map = {}

        # We wouldn't have an edge from a template to a concept node,
        # so we only need to check if the source edge tuple contains a template
        # or a concept id
        inter_template_edges = {
            inter_model_edge[0:2]: inter_model_edge[2]
            for inter_model_edge in compare_graph.inter_model_edges if
            (inter_model_edge[0][1] not in compare_graph.concept_nodes[0] and
             inter_model_edge[0][1] not in compare_graph.concept_nodes[1])
        }

        # same type of checking for as we performed for inter_template_edges
        inter_concept_edges = {
            inter_model_edge[0:2]: inter_model_edge[2]
            for inter_model_edge in compare_graph.inter_model_edges if
            (inter_model_edge[0][1] not in compare_graph.template_nodes[0] and
             inter_model_edge[0][1] not in compare_graph.template_nodes[1])
        }

        # doesn't handle case where if we add the template that has the less
        # specific concept for some reason. If we add the template that
        # contains S instead of the template that has S_old, this code will
        # add S_old and not S even though S_old isn't a present concept in
        # the added template

        for source_target_concept_edge, relation in inter_concept_edges.items():
            replaced_tm_id, replaced_concept_id = source_target_concept_edge[1]
            new_tm_id, new_concept_id = source_target_concept_edge[0]

            replaced_concept = compare_graph.concept_nodes[replaced_tm_id][
                replaced_concept_id]
            new_concept = compare_graph.concept_nodes[new_tm_id][new_concept_id]
            concept_map.setdefault(replaced_concept.name, set())
            concept_map[replaced_concept.name].add(new_concept.name)

        # process templates that are present in a relation first
        # we only process the source template because either it's a template
        # equality relation, so we prioritize the first tm passed in,
        # or it's a refinement relationship in which we want to add the more
        # specific template which is the source template
        for source_target_template_edge, relation in inter_template_edges.items():
            new_tm_id, new_template_id = source_target_template_edge[0]
            new_tm, new_template = compare_graph.template_models[
                new_tm_id], \
                compare_graph.template_nodes[new_tm_id][new_template_id]

            process_template(new_templates, new_template, new_tm,
                             new_parameters, new_initials)

        update_observable_expressions(new_observables, concept_map)

        for outer_template_id, outer_template in enumerate(tm0.templates):
            for inner_template_id, inner_template in enumerate(tm1.templates):
                # only process templates that haven't been pre-processed
                # by checking to see if they aren't present in the
                # inter_edge_dict mapping

                # process inner template first such that outer_template from
                # tm0 take priority
                if not check_template_in_inter_edge_dict(inter_template_edges,
                                                         inner_tm_id,
                                                         inner_template_id):
                    process_template(new_templates, inner_template, tm1,
                                     new_parameters, new_initials)
                if not check_template_in_inter_edge_dict(inter_template_edges,
                                                         outer_tm_id,
                                                         outer_template_id):
                    process_template(new_templates, outer_template, tm0,
                                     new_parameters, new_initials)

    composed_tm = TemplateModel(templates=new_templates,
                                parameters=new_parameters,
                                initials=new_initials,
                                observables=new_observables,
                                annotations=new_annotations,
                                time=new_time)

    if tm0.time and tm1.time:
        substitute_time(composed_tm, tm0.time, tm1.time)

    return composed_tm


def check_template_in_inter_edge_dict(inter_edge_dict, tm_id, template_id):
    """Checks to see the passed-in template in the given template model is
    present in a relation (equality/refinement)

    Parameters
    ----------
    inter_edge_dict :
        Mapping of template relationships between template models
    tm_id :
        The template model id to check
    template_id :
        The template id to check

    Returns
    -------
    :
        True if there exists a relation for the template in the template
        model, else false
    """
    for source_target_edge in inter_edge_dict:
        (t1, t2) = source_target_edge
        if (t1[0] == tm_id and t1[1] == template_id) or (t2[0] == tm_id and
                                                         t2[1] == template_id):
            return True
    return False


def process_template(templates, added_template, added_tm, parameters,
                     initials):
    """Helper method that updates the dictionaries that contain the attributes
    to be used for the new composed template model

    Parameters
    ----------
    templates :
        The list of templates that will be used for the composed template model
    added_template :
        The template that was added to the list of templates for the composed
        template model
    added_tm :
        The input template model to the model_compose method that contains the
        template to be added
    parameters :
        The dictionary of parameters to update that will be used for the
        composed template model
    initials :
        The dictionary of initials to update that will be used for the
        composed template model
    """
    if added_template not in templates:
        templates.append(added_template)
        parameters.update({param_name: added_tm.parameters[param_name] for
                           param_name
                           in added_template.get_parameter_names()})
        initials.update({initial_name: added_tm.initials[initial_name] for
                         initial_name in added_template.get_concept_names()
                         if initial_name in added_tm.initials})


def update_observable_expressions(observables, concept_map):
    """Helper method that updates observables expressions based on which
    concepts were replaced

    Parameters
    ----------
    observables :
        The dictionary of observables to update
    concept_map :
        The mapping of old concepts to the list of new concepts
    """
    for observable in observables.values():
        for old_concept_name, new_concept_list in concept_map.items():
            new_expression = sum([sympy.Symbol(new_concept_name) for
                                  new_concept_name in new_concept_list])
            observable.expression = observable.expression.subs(sympy.Symbol(
                old_concept_name), new_expression)


def substitute_time(tm, time_0, time_1):
    """Helper method that substitutes time in the template model

     Substitute the first time parameter into template rate laws and
     observable expressions of the template model where the second time
     parameter is present

    Parameters
    ----------
    tm :
        The template model that contains the template rate law and
        observable expressions that will be adjusted
    time_0 :
        The time to substitute
    time_1 :
        The time that will be substituted
    """
    for template in tm.templates:
        if template.rate_law:
            template.rate_law = template.rate_law.subs(time_1.units.expression,
                                                       time_0.units.expression)
    for observable in tm.observables.values():
        observable.expression = observable.expression.subs(
            time_1.units.expression, time_0.units.expression)


def annotation_composition(tm0_annot, tm1_annot):
    """Helper method that combines the annotations of the models being composed

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

    new_authors = tm0_annot.authors + tm1_annot.authors
    new_authors = list({author.name: author for author in new_authors}.values())

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

    # prioritize time of tm0
    if tm0_annot.time_start and tm0_annot.time_end and tm0_annot.time_scale:
        time_start = tm0_annot.time_start
        time_end = tm0_annot.time_end
        time_scale = tm0_annot.time_scale
    elif tm1_annot.time_start and tm1_annot.time_end and tm1_annot.time_scale:
        time_start = tm0_annot.time_start
        time_end = tm0_annot.time_end
        time_scale = tm0_annot.time_scale
    else:
        time_start = None
        time_end = None
        time_scale = None

    return Annotations(name=new_name, description=new_description,
                       license=new_license, authors=new_authors,
                       references=new_references, locations=new_locations,
                       pathogens=new_pathogens, dieases=new_diseases,
                       hosts=new_hosts, model_types=new_model_types,
                       time_start=time_start, time_end=time_end,
                       time_scale=time_scale)
