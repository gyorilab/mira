__all__ = ["Annotations", "TemplateModel", "Initial", "Parameter",
           "Distribution", "Observable", "Time", "model_has_grounding"]

import datetime
import sys
from typing import List, Dict, Set, Optional, Mapping, Tuple, Any

import networkx as nx
import sympy
from pydantic import BaseModel, Field
from .templates import *
from .units import Unit
from .utils import safe_parse_expr, SympyExprStr


class Initial(BaseModel):
    """An initial condition."""

    concept: Concept
    value: float

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            SympyExprStr: lambda e: str(e),
        }
        json_decoders = {
            SympyExprStr: lambda e: sympy.parse_expr(e)
        }

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "Initial":
        value = data.pop('value')
        concept_json = data.pop('concept')
        # Get Concept
        concept = Concept.from_json(concept_json)
        return cls(concept=concept, value=value)


class Distribution(BaseModel):
    """A distribution of values for a parameter."""
    type: str = Field(
        description="The type of distribution, e.g. 'uniform', 'normal', etc."
    )
    parameters: Dict[str, float] = Field(
        description="The parameters of the distribution."
    )


class Parameter(Concept):
    """A Parameter is a special type of Concept that carries a value."""
    value: Optional[float] = Field(
        default_factory=None, description="Value of the parameter.")

    distribution: Optional[Distribution] = Field(
        default_factory=None, description="A distribution of values for the parameter."
    )


class Observable(Concept):
    """An observable is a special type of Concept that carries an expression.

    Observables are used to define the readouts of a model, useful when a
    readout is not defined as a state variable but is rather a function of
    state variables.
    """

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            SympyExprStr: lambda e: str(e),
        }
        json_decoders = {
            SympyExprStr: lambda e: safe_parse_expr(e)
        }

    expression: SympyExprStr = Field(
        description="The expression for the observable."
    )

    def substitute_parameter(self, name, value):
        """Substitute a parameter value into the observable expression."""
        self.expression = self.expression.subs(sympy.Symbol(name), value)

    def get_parameter_names(self, known_param_names) -> Set[str]:
        """Get the names of all parameters in the expression."""
        return {str(s) for s in self.expression.free_symbols} & set(known_param_names)


class Time(BaseModel):
    """A special type of Concept that represents time."""
    name: str = Field(
        default="t", description="The symbol of the time variable in the model."
    )
    units: Optional[Unit] = Field(
        description="The units of the time variable."
    )


class Author(BaseModel):
    """A metadata model for an author."""

    name: str = Field(description="The name of the author")


class Annotations(BaseModel):
    """A metadata model for model-level annotations.

    Examples in this metadata model are taken from
    https://www.ebi.ac.uk/biomodels/BIOMD0000000956,
    a well-annotated SIR model in the BioModels database.
    """

    name: Optional[str] = Field(
        description="A human-readable label for the model",
        example="SIR model of scenarios of COVID-19 spread in CA and NY"
    )
    # identifiers: Dict[str, str] = Field(
    #     description="Structured identifiers corresponding to the model artifact "
    #                 "itself, if available, such as a BioModels identifier. Keys in this "
    #                 "dictionary correspond to prefixes in the MIRA Metaregistry and values "
    #                 "correspond to local unique identifiers in the given semantic space.",
    #     default_factory=dict,
    #     example={
    #         "biomodels.db": "BIOMD0000000956",
    #     },
    # )
    description: Optional[str] = Field(
        description="A description of the model",
        example="The coronavirus disease 2019 (COVID-19) pandemic has placed "
        "epidemic modeling at the forefront of worldwide public policy making. "
        "Nonetheless, modeling and forecasting the spread of COVID-19 remains a "
        "challenge. Here, we detail three regional scale models for forecasting "
        "and assessing the course of the pandemic. This work demonstrates the "
        "utility of parsimonious models for early-time data and provides an "
        "accessible framework for generating policy-relevant insights into its "
        "course. We show how these models can be connected to each other and to "
        "time series data for a particular region. Capable of measuring and "
        "forecasting the impacts of social distancing, these models highlight the "
        "dangers of relaxing nonpharmaceutical public health interventions in the "
        "absence of a vaccine or antiviral therapies."
    )
    license: Optional[str] = Field(
        description="Information about the licensing of the model artifact. "
        "Ideally, given as an SPDX identifier like CC0 or CC-BY-4.0. For example, "
        "models from the BioModels databases are all licensed under the CC0 "
        "public attribution license.",
        example="CC0",
    )
    authors: List[Author] = Field(
        default_factory=list,
        description="A list of authors/creators of the model. This is not the same "
        "as the people who e.g., submitted the model to BioModels",
        example=[
            Author(name="Andrea L Bertozzi"),
            Author(name="Elisa Franco"),
            Author(name="George Mohler"),
            Author(name="Martin B Short"),
            Author(name="Daniel Sledge"),
        ],
    )
    references: List[str] = Field(
        default_factory=list,
        description="A list of CURIEs (i.e., <prefix>:<identifier>) corresponding "
        "to literature references that describe the model. Do **not** duplicate the "
        "same publication with different CURIEs (e.g., using pubmed, pmc, and doi)",
        example=["pubmed:32616574"],
    )
    # TODO agree on how we annotate this one, e.g. with a timedelta
    time_scale: Optional[str] = Field(
        description="The granularity of the time element of the model, typically on "
        "the scale of days, weeks, or months for epidemiology models",
        example="day",
    )
    time_start: Optional[datetime.datetime] = Field(
        description="The start time of the applicability of a model, given as a datetime. "
        "When the time scale is not so granular, leave the less granular fields as default, "
        "i.e., if the time scale is on months, give dates like YYYY-MM-01 00:00",
        # example=datetime.datetime(year=2020, month=3, day=1),
    )
    time_end: Optional[datetime.datetime] = Field(
        description="Similar to the start time of the applicability of a model, the end time "
        "is given as a datetime. For example, the Bertozzi 2020 model is applicable between "
        "March and August 2020, so this field is annotated with August 1st, 2020.",
        # example=datetime.datetime(year=2020, month=8, day=1),
    )
    locations: List[str] = Field(
        default_factory=list,
        description="A location or list of locations where this model is applicable, ideally "
        "annotated using a CURIEs referencing a controlled vocabulary such as GeoNames, which "
        "has multiple levels of granularity including city/state/country level terms. For example,"
        "the Bertozzi 2020 model was for New York City (geonames:5128581) and California "
        "(geonames:5332921)",
        example=[
            "geonames:5128581",
            "geonames:5332921",
        ],
    )
    pathogens: List[str] = Field(
        default_factory=list,
        description="The pathogens present in the model, given with CURIEs referencing vocabulary "
        "for taxa, ideally, NCBI Taxonomy. For example, the Bertozzi 2020 model is about "
        "SARS-CoV-2, this is ncbitaxon:2697049. Do not confuse this field with terms for annotating "
        "the disease caused by the pathogen. Note that some models may have multiple pathogens, for "
        "simulating double pandemics such as the interaction with SARS-CoV-2 and the seasonal flu.",
        example=[
            "ncbitaxon:2697049",
        ],
    )
    diseases: List[str] = Field(
        default_factory=list,
        description="The diseases caused by pathogens in the model, given with CURIEs referencing "
        "vocabulary for dieases, such as DOID, EFO, or MONDO. For example, the Bertozzi 2020 model "
        "is about SARS-CoV-2, which causes COVID-19. In the Human Disease Ontology (DOID), this "
        "is referenced by doid:0080600.",
        example=[
            "doid:0080600",
        ],
    )
    hosts: List[str] = Field(
        default_factory=list,
        description="The hosts present in the model, given with CURIEs referencing vocabulary "
        "for taxa, ideally, NCBI Taxonomy. For example, the Bertozzi 2020 model is about "
        "human infection by SARS-CoV-2. Therefore, the appropriate annotation for this field "
        "would be ncbitaxon:9606. Note that some models have multiple hosts, such as Malaria "
        "models that consider humans and mosquitos.",
        example=[
            "ncbitaxon:9606",
        ],

    )
    model_types: List[str] = Field(
        default_factory=list,
        description="This field describes the type(s) of the model using the Mathematical "
        "Modeling Ontology (MAMO), which has terms like 'ordinary differential equation "
        " model', 'population model', etc. These should be annotated as CURIEs in the form "
        "of mamo:<local unique identifier>. For example, the Bertozzi 2020 model is a population "
        "model (mamo:0000028) and ordinary differential equation model (mamo:0000046)",
        example=[
            "mamo:0000028",
            "mamo:0000046",
        ],
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

    observables: Dict[str, Observable] = \
        Field(default_factory=dict,
              description="A list of observables that are readouts "
              "from the model.")

    annotations: Optional[Annotations] = \
        Field(
            default_factory=None,
            description="A structure containing model-level annotations. "
            "Note that all annotations are optional.",
        )

    time: Optional[Time] = \
        Field(
            default_factory=None,
            description="A structure containing time-related annotations. "
            "Note that all annotations are optional.",
        )

    class Config:
        json_encoders = {
            SympyExprStr: lambda e: str(e),
        }
        json_decoders = {
            SympyExprStr: lambda e: safe_parse_expr(e)
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
        if rate_law is None:
            return set()
        params = set()
        if isinstance(rate_law, sympy.Symbol):
            if rate_law.name in self.parameters:
                # add the string name to the set
                params.add(rate_law.name)
        # There are many sympy classes that have args that can occur here
        # so it's better to check for the presence of args
        elif not hasattr(rate_law, 'args'):
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

    def get_all_used_parameters(self):
        """Get all parameters that are actually used in rate laws."""
        used_parameters = set()
        for template in self.templates:
            used_parameters |= template.get_parameter_names()
        return used_parameters

    def eliminate_unused_parameters(self):
        """Remove parameters that are not used in rate laws."""
        used_parameters = self.get_all_used_parameters()
        for k in list(self.parameters.keys()):
            if k not in used_parameters:
                self.parameters.pop(k)

    def eliminate_duplicate_parameter(self, redundant_parameter,
                                      preserved_parameter):
        """Eliminate a duplicate parameter from the model.

        This happens when there are two redundant parameters only one of which
        is actually used in the model. This function removes the redundant
        parameter and updates the rate laws to use the preserved parameter.
        """
        # Update the rate laws
        for template in self.templates:
            template.update_parameter_name(redundant_parameter,
                                           preserved_parameter)
        self.parameters.pop(redundant_parameter)

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

        initials = {}
        for name, value in data.get('initials', {}).items():
            if isinstance(value, float):
                # If the data is just a float, upgrade it to
                # a :class:`Initial` instance
                initials[name] = Initial(
                    concept=concepts[name],
                    value=value,
                )
            else:
                # If the data is not a float, assume it's JSON
                # for a :class:`Initial` instance and parse it to Initial
                initials[name] = Initial.from_json(value)

        # Handle parameters
        parameters = {
            par_key: Parameter.from_json(par_dict)
            for par_key, par_dict in data.get('parameters', {}).items()
        }

        return cls(templates=templates,
                   parameters=parameters,
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
        """Return a mapping from concept keys to concepts that
        appear in this template model's templates.
        """
        return {concept.get_key(): concept for concept in _iter_concepts(self)}

    def get_concepts_name_map(self):
        """Return a mapping from concept names to concepts that
        appear in this template model's templates.
        """
        return {concept.name: concept for concept in _iter_concepts(self)}

    def get_concept(self, name: str) -> Optional[Concept]:
        """Return the first concept that has the given name."""
        names = self.get_concepts_by_name(name)
        if names:
            return names[0]
        return None

    def reset_base_names(self):
        """Reset the base names of all concepts in this model to the current name."""
        for template in self.templates:
            for concept in template.get_concepts():
                concept._base_name = concept.name
        for initial in self.initials.values():
            initial.concept._base_name = initial.concept.name

    def get_concepts_by_name(self, name: str) -> List[Concept]:
        """Return a list of all concepts that have the given name.

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
                                 observables=self.observables,
                                 annotations=self.annotations,
                                 time=self.time)
        elif parameter_mapping is None:
            initials = (self.initials or {})
            initials.update(initial_mapping or {})
            return TemplateModel(
                templates=self.templates + [template],
                initials=initials,
                parameters=self.parameters,
                annotations=self.annotations,
                observables=self.observables,
                time=self.time,
            )
        elif initial_mapping is None:
            parameters = (self.parameters or {})
            parameters.update(parameter_mapping or {})
            return TemplateModel(
                templates=self.templates + [template],
                parameters=parameters,
                initials=self.initials,
                annotations=self.annotations,
                observables=self.observables,
                time=self.time,
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
                observables=self.observables,
                time=self.time,
            )

    def add_transition(
            self,
            transition_name: str = None,
            subject_concept: Concept = None,
            outcome_concept: Concept = None,
            rate_law_sympy: SympyExprStr = None,
            parameter: Optional[Parameter] = None,
            params_dict: Mapping = None
    ) -> "TemplateModel":
        """Add support for Natural templates between a source and an outcome.
        Multiple parameters can be added explicitly or implicitly
        """
        if subject_concept and outcome_concept:
            template = NaturalConversion(
                name=transition_name,
                subject=subject_concept,
                outcome=outcome_concept,
                rate_law=rate_law_sympy
            )
        elif subject_concept and outcome_concept is None:
            template = NaturalDegradation(
                name=transition_name,
                subject=subject_concept,
                rate_law=rate_law_sympy)
        else:
            template = NaturalProduction(
                name=transition_name,
                outcome=outcome_concept,
                rate_law=rate_law_sympy
            )
        if params_dict:
            # add explicitly parameters to template model
            for free_symbol_sympy in template.rate_law.free_symbols:
                free_symbol_str = str(free_symbol_sympy)
                if free_symbol_str in params_dict:
                    name = params_dict[free_symbol_str].get('display_name')
                    value = params_dict[free_symbol_str].get('value')
                    units = params_dict[free_symbol_str].get('units')
                    distribution = params_dict[free_symbol_str].get('distribution')
                    self.add_parameter(parameter_id=free_symbol_str, name=name,
                                       value=value,
                                       distribution=distribution,
                                       units_mathml=units)
        # If there are no explicitly defined parameters
        # Extract new parameters from rate laws without any other information about that parameter
        else:
            free_symbol_str = {str(symbol) for symbol in template.rate_law.free_symbols}

            # Remove subject name from list of free symbols if the template is not NaturalProduction
            if not isinstance(template, NaturalProduction):
                free_symbol_str -= {template.subject.name}
            free_symbol_str -= set(self.parameters)
            for new_param in free_symbol_str:
                self.add_parameter(new_param)

        if parameter:
            template.set_mass_action_rate_law(parameter.name)
        pm = {parameter.name: parameter} if parameter else None
        return self.add_template(template, parameter_mapping=pm)

    def substitute_parameter(self, name, value=None):
        """Substitute a parameter with a value."""
        if name not in self.parameters:
            return
        if value is None:
            value = self.parameters[name].value
        self.parameters = {k: v for k, v in self.parameters.items()
                           if k != name}
        for template in self.templates:
            template.substitute_parameter(name, value)
        for observable in self.observables.values():
            observable.substitute_parameter(name, value)

    def add_parameter(self, parameter_id: str,
                      name: str = None,
                      value: float = None,
                      distribution=None,
                      units_mathml: str = None):
        distribution = Distribution(**distribution) if distribution else None
        if units_mathml:
            units = {
                'expression': mathml_to_expression(units_mathml),
                'expression_mathml': units_mathml
            }
        else:
            units = None

        data = {
            'name': parameter_id,
            'display_name': name,
            'value': value,
            'distribution': distribution,
            'units': units
        }

        parameter = Parameter(**data)
        self.parameters[parameter_id] = parameter

    def eliminate_parameter(self, name):
        """Eliminate a parameter from the model by substituting 0."""
        self.substitute_parameter(name, value=0)

    def set_parameters(self, param_dict):
        """Set the parameters of this model to the values in the given dict."""
        for name, value in param_dict.items():
            if self.parameters and name in self.parameters:
                self.parameters[name].value = value

    def set_initials(self, initial_dict):
        """Set the initials of this model to the values in the given dict."""
        for name, value in initial_dict.items():
            if self.initials and name in self.initials:
                self.initials[name].value = value


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
        elif isinstance(template, ControlledDegradation):
            yield from (template.subject, template.controller)
        elif isinstance(template, ControlledProduction):
            yield from (template.outcome, template.controller)
        elif isinstance(template, GroupedControlledProduction):
            yield from template.controllers
            yield template.outcome
        elif isinstance(template, GroupedControlledDegradation):
            yield from template.controllers
            yield template.subject
        elif isinstance(template, StaticConcept):
            yield template.subject
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

# Circular import error if we were to import this method from mira/metamodel/io.py as that file imports TemplateModel
def mathml_to_expression(xml_str: str) -> sympy.Expr:
    """Convert a MathML string to a sympy expression."""
    from sbmlmath import SBMLMathMLParser
    template = """<?xml version="1.0" encoding="UTF-8"?>
    <math xmlns="http://www.w3.org/1998/Math/MathML">
    {xml_str}
    </math>"""
    xml_str = template.format(xml_str=xml_str)
    return SBMLMathMLParser().parse_str(xml_str)
