__all__ = ["TemplateModel", "Initial", "Parameter", "model_has_grounding"]

import sys
from typing import List, Dict, Set, Optional, Mapping, Tuple

import networkx as nx
import sympy
from pydantic import BaseModel, Field

from .templates import Template, Concept, \
    NaturalConversion, ControlledConversion, GroupedControlledConversion, \
    NaturalDegradation, NaturalProduction, SpecifiedTemplate, SympyExprStr


class Initial(BaseModel):
    """An initial condition."""

    concept: Concept
    value: float


class Parameter(Concept):
    """A Parameter is a special type of Concept that carries a value."""
    value: float = Field(
        default_factory=None, description="Value of the parameter."
    )


class TemplateModel(BaseModel):
    """A template model."""

    templates: List[SpecifiedTemplate] = Field(
        ..., description="A list of any child class of Templates"
    )
    parameters: Dict[str, Parameter] = \
        Field(default_factory=dict,
              description="A dict of parameter values where keys correspond "
                          "to how the parameter appears in rate laws.")
    initials: Dict[str, Initial] = \
        Field(default_factory=dict,
              description="A dict of initial condition values where keys"
                          "correspond to concept names they apply to.")

    annotations: Dict[str, List[str]] = \
        Field(default_factory=dict,
              description="A dict of annotations where keys correspond to "
                          "the annotation name and values to the annotation "
                          "value.")

    class Config:
        json_encoders = {
            SympyExprStr: lambda e: str(e),
        }
        json_decoders = {
            SympyExprStr: lambda e: sympy.parse_expr(e)
        }

    def get_parameters_from_rate_law(self, rate_law) -> Set[str]:
        """Given a rate law, find its elements that are model parameters.

        Rate laws consist of some combination of participants, rate parameters
        and potentially other factors. This function finds those elements of
        rate laws that are rate parameters.

        Parameters
        ----------
        rate_law :
            A sympy expression or symbol, whose names are extracted

        Returns
        -------
        :
            A set of parameter names (as strings)
        """
        if not rate_law:
            return set()
        params = set()
        if isinstance(rate_law, sympy.Symbol):
            if rate_law.name in self.parameters:
                # add the string name to the set
                params.add(rate_law.name)
        elif not isinstance(rate_law, sympy.Expr):
            raise ValueError(f"Rate law is of invalid type {type(rate_law)}: {rate_law}")
        else:
            for arg in rate_law.args:
                params |= self.get_parameters_from_rate_law(arg)
        return params

    def update_parameters(self, parameter_dict):
        for k, v in parameter_dict.items():
            if k in self.parameters:
                self.parameters[k].value = v
            else:
                self.parameters[k] = Parameter(name=k, value=v)

    @classmethod
    def from_json(cls, data) -> "TemplateModel":
        local_symbols = {p: sympy.Symbol(p) for p in data.get('parameters', [])}
        for template_dict in data.get('templates', []):
            # We need to figure out the template class based on the type
            # entry in the data
            template_cls = getattr(sys.modules[__name__], template_dict['type'])
            for concept_key in template_cls.concept_keys:
                # Note the special handling here for list-like vs single
                # concepts
                concept_data = template_dict.get(concept_key)
                if concept_data:
                    if not isinstance(concept_data, list):
                        concept_data = [concept_data]
                    for concept_dict in concept_data:
                        if concept_dict.get('name'):
                            local_symbols[concept_dict.get('name')] = \
                                sympy.Symbol(concept_dict.get('name'))
        # We can now use these symbols to deserialize rate laws
        templates = [Template.from_json(template, rate_symbols=local_symbols)
                     for template in data["templates"]]

        #: A lookup from concept name in the model to the full
        #: concept object to be used for preparing initial values
        concepts = {
            concept.name: concept
            for template in templates
            for concept in template.get_concepts()
        }

        initials = {
            name: (
                Initial(
                    concept=concepts[name],
                    value=value,
                )
                # If the data is just a float, upgrade it to
                # a :class:`Initial` instance
                if isinstance(value, float)
                # If the data is not a float, assume it's JSON
                # for a :class:`Initial` instance
                else value
            )
            for name, value in data.get('initials', {}).items()
        }

        return cls(templates=templates,
                   parameters=data.get('parameters', {}),
                   initials=initials,
                   annotations=data.get('annotations'))

    def generate_model_graph(self) -> nx.DiGraph:
        graph = nx.DiGraph()
        for template in self.templates:

            # Add node for template itself
            node_id = get_template_graph_key(template)
            graph.add_node(
                node_id,
                type=template.type,
                template_key=template.get_key(),
                label=template.type,
                color="orange",
                shape="record",
            )

            # Add in/outgoing nodes for the concepts of this template
            for role, concepts in template.get_concepts_by_role().items():
                for concept in concepts if isinstance(concepts, list) else [concepts]:
                    # Note: this includes the node's name as well as its
                    # grounding
                    concept_key = get_concept_graph_key(concept)
                    # Note that this doesn't include the concept's name
                    # in the key
                    concept_identity_key = concept.get_key()
                    context_str = "\n".join(
                        f"{k}-{v}" for k, v in concept.context.items()
                    )
                    context_str = "\n" + context_str if context_str else ""
                    if concept.get_included_identifiers():
                        label = (
                            f"{concept.name}\n({concept.get_curie_str()})"
                            f"{context_str}"
                        )
                    else:
                        label = f"{concept.name}\n(ungrounded){context_str}"
                    graph.add_node(
                        concept_key,
                        label=label,
                        color="orange",
                        concept_identity_key=concept_identity_key,
                    )
                    role_label = "controller" if role == "controllers" \
                        else role
                    if role_label in {"controller", "subject"}:
                        source, target = concept_key, node_id
                    else:
                        source, target = node_id, concept_key
                    graph.add_edge(source, target, label=role_label)

        return graph

    def draw_graph(
        self, path: str, prog: str = "dot", args: str = "", format: Optional[str] = None
    ):
        """Draw a pygraphviz graph of the TemplateModel

        Parameters
        ----------
        path :
            The path to the output file
        prog :
            The graphviz layout program to use, such as "dot", "neato", etc.
        format :
            Set the file format explicitly
        args :
            Additional arguments to pass to the graphviz bash program as a
            string. Example: args="-Nshape=box -Edir=forward -Ecolor=red"
        """
        # draw graph
        graph = self.generate_model_graph()
        agraph = nx.nx_agraph.to_agraph(graph)
        agraph.draw(path, format=format, prog=prog, args=args)

    def draw_jupyter(self, path: str = "model.png", prog: str = "dot", args: str = "", format: Optional[str] = None):
        """Display in jupyter."""
        from IPython.display import Image

        self.draw_graph(path=path, prog=prog, args=args, format=format)

        return Image(path)

    def graph_as_json(self) -> Dict:
        """Serialize the TemaplateModel graph as node-link data"""
        graph = self.generate_model_graph()
        return nx.node_link_data(graph)

    def print_params_table(self):
        import tabulate
        contexts = set()
        for key, param in self.parameters.items():
            contexts |= set(param.context.keys())

        header = ['name', 'identifier'] + sorted(contexts)
        rows = [header]
        for key, param in self.parameters.items():
            identifier_curie = ':'.join(list(param.identifiers.items())[0])
            context_entries = [param.context.get(context)
                               for context in sorted(contexts)]
            rows.append([key, identifier_curie] + context_entries)

        print(tabulate.tabulate(rows, headers='firstrow'))

    def get_concepts_map(self):
        """
        Get a mapping from concept keys to concepts that
        appear in this template models' templates.
        """
        return {concept.get_key(): concept for concept in _iter_concepts(self)}

    def get_concepts_by_name(self, name: str) -> List[Concept]:
        """Get a list of all concepts that have the given name.

        .. warning::

            this could give duplicates if there are nodes with
            compositional grounding
        """
        name = name.casefold()
        return [
            concept
            for template in self.templates
            for concept in template.get_concepts()
            if concept.name.casefold() == name
        ]

    def extend(self, template_model: "TemplateModel",
               parameter_mapping: Optional[Mapping[str, Parameter]] = None,
               initial_mapping: Optional[Mapping[str, Initial]] = None):
        """Extend this template model with another template model."""
        model = self
        for template in template_model.templates:
            model = model.add_template(template,
                                       parameter_mapping=parameter_mapping,
                                       initial_mapping=initial_mapping)
        return model

    def add_template(
            self,
            template: Template,
            parameter_mapping: Optional[Mapping[str, Parameter]] = None,
            initial_mapping: Optional[Mapping[str, Initial]] = None,
    ) -> "TemplateModel":
        """Add a template to the model

        Parameters
        ----------
        template :
            The template to add
        parameter_mapping :
            A mapping from parameter names in the template to Parameter
            instances in the model.
        initial_mapping :
            A mapping from concept names in the template to Initial
            instances in the model

        Returns
        -------
        :
            A new model with the additional template
        """
        # todo: handle adding parameters and initials
        if parameter_mapping is None and initial_mapping is None:
            return TemplateModel(templates=self.templates + [template],
                                 parameters=self.parameters,
                                 initials=self.initials,
                                 annotations=self.annotations)
        elif parameter_mapping is None:
            initials = (self.initials or {})
            initials.update(initial_mapping or {})
            return TemplateModel(
                templates=self.templates + [template],
                initials=initials,
                parameters=self.parameters,
                annotations=self.annotations,
            )
        elif initial_mapping is None:
            parameters = (self.parameters or {})
            parameters.update(parameter_mapping or {})
            return TemplateModel(
                templates=self.templates + [template],
                parameters=parameters,
                initials=self.initials,
                annotations=self.annotations,
            )
        else:
            initials = (self.initials or {})
            initials = initials.update(initial_mapping or {})
            parameters = (self.parameters or {})
            parameters.update(parameter_mapping or {})
            return TemplateModel(
                templates=self.templates + [template],
                parameters=parameters,
                initials=initials,
                annotations=self.annotations,
            )

    def add_transition(
        self,
        subject_concept: Concept,
        outcome_concept: Concept,
        parameter: Optional[Parameter] = None,
    ) -> "TemplateModel":
        """Add a NaturalConversion between a source and an outcome.

        We assume mass action kinetics with a single parameter.
        """
        template = NaturalConversion(
            subject=subject_concept,
            outcome=outcome_concept,
        )
        if parameter:
            template.set_mass_action_rate_law(parameter.name)
        pm = {parameter.name: parameter} if parameter else None
        return self.add_template(template, parameter_mapping=pm)


def _iter_concepts(template_model: TemplateModel):
    for template in template_model.templates:
        if isinstance(template, ControlledConversion):
            yield from (template.subject, template.outcome, template.controller)
        elif isinstance(template, NaturalConversion):
            yield from (template.subject, template.outcome)
        elif isinstance(template, GroupedControlledConversion):
            yield from template.controllers
            yield from (template.subject, template.outcome)
        elif isinstance(template, NaturalDegradation):
            yield template.subject
        elif isinstance(template, NaturalProduction):
            yield template.outcome
        else:
            raise TypeError(f"could not handle template: {template}")


def get_concept_graph_key(concept: Concept) -> Tuple[str, ...]:
    grounding_key = ("identity", concept.get_curie_str())
    context_key = tuple(i for t in sorted(concept.context.items()) for i in t)
    key = (concept.name,) + grounding_key + context_key
    key = tuple(key) if len(key) > 1 else (key[0],)
    return key


def get_template_graph_key(template: Template) -> Tuple[str, ...]:
    name: str = template.type
    key = [name]
    for concept in template.get_concepts():
        for key_part in get_concept_graph_key(concept):
            key.append(key_part)

    if len(key) > 1:
        return tuple(key)
    else:
        return key[0],


def model_has_grounding(template_model: TemplateModel, prefix: str,
                        identifier: str) -> bool:
    """Return whether a model contains a given grounding in any role."""
    search_curie = f'{prefix}:{identifier}'
    for template in template_model.templates:
        for concept in template.get_concepts():
            for concept_prefix, concept_id in concept.identifiers.items():
                if concept_prefix == prefix and concept_id == identifier:
                    return True
            for key, curie in concept.context.items():
                if curie == search_curie:
                    return True
    for key, param in template_model.parameters.items():
        for param_prefix, param_id in param.identifiers.items():
            if param_prefix == prefix and param_id == identifier:
                return True
        for key, curie in param.context.items():
            if curie == search_curie:
                return True
    return False
