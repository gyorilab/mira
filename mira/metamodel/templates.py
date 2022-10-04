"""
Data models for metamodel templates.

Regenerate the JSON schema by running ``python -m mira.metamodel.templates``.
"""
__all__ = [
    "Concept",
    "Template",
    "Provenance",
    "ControlledConversion",
    "NaturalConversion",
    "NaturalProduction",
    "NaturalDegradation",
    "GroupedControlledConversion",
    "TemplateModel",
    "TemplateModelDelta",
    "RefinementClosure",
    "get_json_schema",
    "templates_equal",
    "assert_concept_context_refinement",
]

import json
import logging
import sys
from collections import ChainMap, defaultdict
from itertools import product
from pathlib import Path
from typing import List, Mapping, Optional, Tuple, Literal, Callable, Union, Dict

import pydantic
import networkx as nx
from networkx import DiGraph
from pydantic import BaseModel, Field

try:
    from typing import Annotated  # py39+
except ImportError:
    from typing_extensions import Annotated


HERE = Path(__file__).parent.resolve()
SCHEMA_PATH = HERE.joinpath("schema.json")

logger = logging.getLogger(__name__)


class Config(BaseModel):
    """Config determining how keys are generated"""

    prefix_priority: List[str]


DEFAULT_CONFIG = Config(
    prefix_priority=[
        "ido",
    ],
)


class Concept(BaseModel):
    """A concept is specified by its identifier(s), name, and - optionally -
    its context.
    """

    name: str = Field(..., description="The name of the concept.")
    identifiers: Mapping[str, str] = Field(
        default_factory=dict, description="A mapping of namespaces to identifiers."
    )
    context: Mapping[str, str] = Field(
        default_factory=dict, description="A mapping of context keys to values."
    )

    def with_context(self, **context) -> "Concept":
        """Return this concept with extra context."""
        return Concept(
            name=self.name,
            identifiers=self.identifiers,
            context=dict(ChainMap(context, self.context)),
        )

    def get_curie(self, config: Optional[Config] = None) -> Tuple[str, str]:
        """Get the priority prefix/identifier pair for this concept."""
        if config is None:
            config = DEFAULT_CONFIG
        if not self.identifiers:
            return "", self.name
        for prefix in config.prefix_priority:
            identifier = self.identifiers.get(prefix)
            if identifier:
                return prefix, identifier
        return sorted(self.identifiers.items())[0]

    def get_curie_str(self, config: Optional[Config] = None) -> str:
        """Get the priority prefix/identifier as a CURIE string."""
        return ":".join(self.get_curie(config=config))

    def get_key(self, config: Optional[Config] = None):
        return (
            self.get_curie(config=config),
            tuple(sorted(self.context.items())),
        )

    def is_equal_to(self, other: "Concept", with_context: bool = False) -> bool:
        """Test for equality between concepts

        Parameters
        ----------
        other :
            Other Concept to test equality with
        with_context :
            If True, do not consider the two Concepts equal unless they also
            have exactly the same context. If there is no context,
            ``with_context`` has no effect.

        Returns
        -------
        :
            True if ``other`` is the same Concept as this one
        """
        if not isinstance(other, Concept):
            return False

        # With context
        if with_context:
            # Check that the same keys appear in both
            if set(self.context.keys()) != set(other.context.keys()):
                return False

            # Check that the values are the same
            for k1, v1 in self.context.items():
                if v1 != other.context[k1]:
                    return False

        # Check that they are grounded to the same identifier
        if len(self.identifiers) > 0 and len(other.identifiers) > 0:
            if self.get_curie() != other.get_curie():
                return False
            else:
                pass
        # If both are ungrounded use name equality as fallback
        elif len(self.identifiers) == 0 and len(other.identifiers) == 0:
            if self.name.lower() != self.name.lower():
                return False

        # Here we know that we have
        # len(self.identifiers) > 0 XOR len(other.identifiers) > 0
        else:
            return False

        return True

    def refinement_of(
        self,
        other: "Concept",
        refinement_func: Callable[[str, str], bool],
        with_context: bool = False,
    ) -> bool:
        """Check if this Concept is a more detailed version of another

        Parameters
        ----------
        other :
            The other Concept to compare with. Assumed to be less detailed.
        with_context :
            If True, also consider the context of the Concepts for the
            refinement.
        refinement_func :
            A function that given a source/more detailed entity and a
            target/less detailed entity checks if they are in a child-parent and
            returns a boolean.

        Returns
        -------
        :
            True if this Concept is a refinement of another Concept
        """
        if not isinstance(other, Concept):
            return False

        contextual_refinement = False
        if with_context and assert_concept_context_refinement(
            refined_concept=self, other_concept=other
        ):
            contextual_refinement = True

        # Check if this concept is a child term to other?
        if len(self.identifiers) > 0 and len(other.identifiers) > 0:
            # Check if other is a parent of this concept
            this_curie = ":".join(self.get_curie())
            other_curie = ":".join(other.get_curie())
            ontological_refinement = refinement_func(this_curie, other_curie)

        # Any of them are ungrounded -> cannot know if there is a refinement
        # -> return False
        # len(self.identifiers) == 0 or len(other.identifiers) == 0
        else:
            ontological_refinement = False

        if with_context:
            return ontological_refinement or \
                   self.is_equal_to(other) and contextual_refinement
        return ontological_refinement


class Template(BaseModel):
    """The Template is a parent class for model processes"""

    @classmethod
    def from_json(cls, data) -> "Template":
        template_type = data.pop("type")
        stmt_cls = getattr(sys.modules[__name__], template_type)
        return stmt_cls(**data)

    def is_equal_to(self, other: "Template", with_context: bool = False) -> bool:
        """Check if this template is equal to another template

        Parameters
        ----------
        other :
            The other template to check for equality with this one with
        with_context :
            If True, the contexts are taken into account when checking for
            equality. Default: False.

        Returns
        -------
        :
            True if the other Template is equal to this Template
        """
        if not isinstance(other, Template):
            return False
        return templates_equal(self, other, with_context)

    def refinement_of(
        self,
        other: "Template",
        refinement_func: Callable[[str, str], bool],
        with_context: bool = False,
    ) -> bool:
        """Check if this template is a more detailed version of another

        Parameters
        ----------
        other :
            The other template to compare with. Is assumed to be less
            detailed than this template.
        with_context :
            If True, also consider the context of Templates' Concepts for the
            refinement.
        refinement_func :
            A function that given a source/more detailed entity and a
            target/less detailed entity checks if they are in a child-parent
            relationship and returns a boolean.

        Returns
        -------
        :
            True if this Template is a refinement of the other Template.
        """
        if not isinstance(other, Template):
            return False

        if self.type != other.type:
            return False

        for field_name in self.dict(exclude={"type"}):
            this_value = getattr(self, field_name)

            # Check refinement for any attribute that is a Concept; this is
            # strict in the sense that unless every concept of this template is a
            # refinement of the other, the Template as a whole cannot be
            # considered a refinement
            if isinstance(this_value, Concept):
                other_concept = getattr(other, field_name)
                if not this_value.refinement_of(
                    other_concept,
                    refinement_func=refinement_func,
                    with_context=with_context
                ):
                    return False

            elif isinstance(this_value, list):
                if len(this_value) > 0:
                    # List[Concept] from e.g. GroupedControlledConversion
                    if isinstance(this_value[0], Concept):
                        other_concept_list = getattr(other, field_name)
                        if len(other_concept_list) == 0:
                            return False

                        # Check if there exists at least one refinement
                        # relation in the other's list for every concept in
                        # this list. Also check the all Concepts in the
                        # other's list have at least one refinement relation

                        has_refinement = set()
                        for this_concept in this_value:
                            refinement_found = False
                            for other_concept_item in other_concept_list:
                                if this_concept.refinement_of(
                                        other_concept_item,
                                        refinement_func=refinement_func
                                ):
                                    has_refinement.add(other_concept_item.get_key())
                                    refinement_found = True
                            if not refinement_found:
                                return False

                        # Check if all "less refined" concepts in list have
                        # a refinement relation
                        if len(has_refinement) < len(other_concept_list):
                            return False

                    elif isinstance(this_value[0], Provenance):
                        # Skip Provenance
                        continue

                    else:
                        logger.warning(
                            f"Unhandled type List[{type(this_value[0])}] "
                            f"for refinement"
                        )

                # len == 0 for this Concept's controllers
                else:
                    # If other's controllers has any Concepts, this can't be
                    # a refinement of other
                    if field_name == "controllers" and \
                            len(getattr(other, field_name)) > 0:
                        return False
            else:
                logger.warning(f"Unhandled type {type(this_value)}")

        return True

    def get_concepts(self):
        """Return the concepts in this template."""
        raise NotImplementedError


class Provenance(BaseModel):
    pass


class ControlledConversion(Template):
    """Specifies a process of controlled conversion from subject to outcome,
    controlled by the controller."""

    type: Literal["ControlledConversion"] = Field("ControlledConversion", const=True)
    controller: Concept
    subject: Concept
    outcome: Concept
    provenance: List[Provenance] = Field(default_factory=list)

    def with_context(self, **context) -> "ControlledConversion":
        """Return a copy of this template with context added"""
        return self.__class__(
            type=self.type,
            subject=self.subject.with_context(**context),
            outcome=self.outcome.with_context(**context),
            controller=self.controller.with_context(**context),
            provenance=self.provenance,
        )

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.subject.get_key(config=config),
            self.controller.get_key(config=config),
            self.outcome.get_key(config=config),
        )

    def get_concepts(self):
        """Return the concepts in this template."""
        return [self.controller, self.subject, self.outcome]

    def get_concepts_by_role(self):
        return {
            "controller": self.controller,
            "subject": self.subject,
            "outcome": self.outcome
        }


class GroupedControlledConversion(Template):
    type: Literal["GroupedControlledConversion"] = Field("GroupedControlledConversion", const=True)
    controllers: List[Concept]
    subject: Concept
    outcome: Concept
    provenance: List[Provenance] = Field(default_factory=list)

    def with_context(self, **context) -> "GroupedControlledConversion":
        """Return a copy of this template with context added"""
        return self.__class__(
            type=self.type,
            controllers=[c.with_context(**context) for c in self.controllers],
            subject=self.subject.with_context(**context),
            outcome=self.outcome.with_context(**context),
            provenance=self.provenance,
        )

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            *tuple(
                c.get_key(config=config)
                for c in sorted(self.controllers, key=lambda c: c.get_curie())
            ),
            self.subject.get_key(config=config),
            self.outcome.get_key(config=config),
        )

    def get_concepts(self):
        """Return the concepts in this template."""
        return self.controllers + [self.subject, self.outcome]

    def get_concepts_by_role(self):
        return {
            "controllers": self.controllers,
            "subject": self.subject,
            "outcome": self.outcome
        }

class NaturalConversion(Template):
    """Specifies a process of natural conversion from subject to outcome"""

    type: Literal["NaturalConversion"] = Field("NaturalConversion", const=True)
    subject: Concept
    outcome: Concept
    provenance: List[Provenance] = Field(default_factory=list)

    def with_context(self, **context) -> "NaturalConversion":
        """Return a copy of this template with context added"""
        return self.__class__(
            type=self.type,
            subject=self.subject.with_context(**context),
            outcome=self.outcome.with_context(**context),
            provenance=self.provenance,
        )

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.subject.get_key(config=config),
            self.outcome.get_key(config=config),
        )

    def get_concepts(self):
        """Return the concepts in this template."""
        return [self.subject, self.outcome]

    def get_concepts_by_role(self):
        return {
            "subject": self.subject,
            "outcome": self.outcome
        }


class NaturalProduction(Template):
    """A template for the production of a species at a constant rate."""

    type: Literal["NaturalProduction"] = Field("NaturalProduction", const=True)
    outcome: Concept
    provenance: List[Provenance] = Field(default_factory=list)

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.outcome.get_key(config=config),
        )

    def get_concepts(self):
        """Return the concepts in this template."""
        return [self.outcome]

    def get_concepts_by_role(self):
        return {
            "outcome": self.outcome
        }


class NaturalDegradation(Template):
    """A template for the degradataion of a species at a proportional rate to its amount."""

    type: Literal["NaturalDegradation"] = Field("NaturalDegradation", const=True)
    subject: Concept
    provenance: List[Provenance] = Field(default_factory=list)

    def get_key(self, config: Optional[Config] = None):
        return (
            self.type,
            self.subject.get_key(config=config),
        )

    def get_concepts(self):
        """Return the concepts in this template."""
        return [self.subject]

    def get_concepts_by_role(self):
        return {
            "subject": self.subject
        }


def get_json_schema():
    """Get the JSON schema for MIRA."""
    rv = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "https://raw.githubusercontent.com/indralab/mira/main/mira/metamodel/schema.json",
    }
    rv.update(
        pydantic.schema.schema(
            [
                Concept,
                Template,
                *Template.__subclasses__(),
            ],
            title="MIRA Metamodel Template Schema",
            description="MIRA metamodel templates give a high-level abstraction of modeling appropriate for many domains.",
        )
    )
    return rv


def templates_equal(templ: Template, other_templ: Template, with_context: bool) -> bool:
    """Check if two Template objects are equal

    Parameters
    ----------
    templ :
        A template to compare.
    other_templ :
        The other template to compare.
    with_context :
        If True, also check the contexts of the contained Concepts of the
        Template.

    Returns
    -------
    :
        True if the two Template objects are equal.
    """
    if templ.type != other_templ.type:
        return False

    other_dict = other_templ.__dict__
    for key, value in templ.__dict__.items():
        # Already checked type
        if key == "type":
            continue

        if isinstance(value, Concept):
            other_concept: Concept = other_dict[key]
            if not value.is_equal_to(other_concept, with_context=with_context):
                return False

        elif isinstance(value, list):
            # Assert that we have the same number of things in the list
            if len(value) != len(other_dict[key]):
                return False

            elif len(value):
                # Assumed to be same length
                if isinstance(value[0], Concept):
                    for this_conc, other_conc in zip(value, other_dict[key]):
                        if not this_conc.is_equal_to(
                                other_conc, with_context=with_context
                        ):
                            return False
                else:
                    raise NotImplementedError(
                        f"No comparison implemented for type "
                        f"List[{type(value[0])}] of Template"
                    )
            # Empty list

        else:
            raise NotImplementedError(
                f"No comparison implemented for type {type(value)} for Template"
            )
    return True


def assert_concept_context_refinement(refined_concept: Concept, other_concept: Concept) -> bool:
    """Check if one Concept's context is a refinement of another Concept's

    Special case:
    - Both contexts are empty => special case of equal context => False

    Parameters
    ----------
    refined_concept :
        The assumed *more* detailed Concept
    other_concept :
        The assumed *less* detailed Concept

    Returns
    -------
    :
        True if the Concept `refined_concept` truly is strictly more detailed
        than `other_concept`
    """
    refined_context = refined_concept.context
    other_context = other_concept.context
    # 1. False if no context for both
    if len(refined_context) == 0 and len(other_context) == 0:
        return False
    # 2. True if refined concept has context and the other one not
    elif len(refined_context) > 0 and len(other_context) == 0:
        return True
    # 3. False if refined concept does not have context and the other does
    elif len(refined_context) == 0 and len(other_context) > 0:
        return False
    # 4. Both have context
    else:
        # 1. Exactly equal context keys -> False
        # 2. False if refined Concept context is a subset of other context
        #
        # NOTE: issubset is not strict, i.e. is True for equal sets, therefore
        # we need to check for refined.issubset(other) first to be sure that
        # cases 1. and 2. are ruled out when 3. is evaluated
        if set(refined_context.keys()).issubset(other_context.keys()):
            return False

        # 3. Other Concept context is a subset; check equality for the matches
        elif set(other_context.keys()).issubset(refined_context):
            for other_context_key, other_context_value in other_context.items():
                if refined_context[other_context_key] != other_context_value:
                    return False

        # 4. Both Concepts have context, but they are different -> cannot be a
        #    refinement -> False
        elif set(other_context.keys()).symmetric_difference(set(refined_context.keys())):
            return False

        # 5. All cases should be covered, but in case something is missing
        else:
            raise ValueError("Unhandled logic, missing at least one logical option")

    return True


# Needed for proper parsing by FastAPI
SpecifiedTemplate = Annotated[
    Union[
        NaturalConversion, ControlledConversion, NaturalDegradation, NaturalProduction, GroupedControlledConversion,
    ],
    Field(description="Any child class of a Template", discriminator="type"),
]


class TemplateModel(BaseModel):
    templates: List[SpecifiedTemplate] = Field(
        ..., description="A list of any child class of Templates"
    )

    @classmethod
    def from_json(cls, data) -> "TemplateModel":
        templates = [Template.from_json(template) for template in data["templates"]]
        return cls(templates=templates)

    def generate_model_graph(self) -> DiGraph:
        graph = DiGraph()
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
                    concept_key = get_concept_graph_key(concept)
                    graph.add_node(
                        concept_key,
                        label=concept.name,
                        color="orange"
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
            string. Example: "args="-Nshape=box -Edir=forward -Ecolor=red "
        """
        # draw graph
        graph = self.generate_model_graph()
        agraph = nx.nx_agraph.to_agraph(graph)
        agraph.draw(path, format=format, prog=prog, args=args)

    def graph_as_json(self) -> Dict:
        """Serialize the TemaplateModel graph as node-link data"""
        graph = self.generate_model_graph()
        return nx.node_link_data(graph)


class TemplateModelDelta:
    """Defines the differences between TemplateModels as a networkx graph"""

    def __init__(
        self,
        template_model1: TemplateModel,
        template_model2: TemplateModel,
        refinement_function: Callable[[str, str], bool],
        tag1: str = "1",
        tag2: str = "2",
        tag1_color: str = "orange",
        tag2_color: str = "blue",
        merge_color: str = "red",
    ):
        self.refinement_func = refinement_function
        self.template_model1 = template_model1
        self.templ1_graph = template_model1.generate_model_graph()
        self.tag1 = tag1
        self.tag1_color = tag1_color
        self.template_model2 = template_model2
        self.templ2_graph = template_model2.generate_model_graph()
        self.tag2 = tag2
        self.tag2_color = tag2_color
        self.merge_color = merge_color
        self.comparison_graph = DiGraph()
        self.comparison_graph.graph["rankdir"] = "LR"  # transposed node tables
        self._assemble_comparison()

    def _add_node(self, template: Template, tag: str):
        # Get a unique identifier for node
        node_id = (*get_template_graph_key(template), tag)
        self.comparison_graph.add_node(
            node_id,
            type=template.type,
            template_key=template.get_key(),
            label=template.type,
            color=self.tag1_color if tag == self.tag1 else self.tag2_color,
            shape="record",
        )
        return node_id

    def _add_edge(
        self,
        source: Template,
        source_tag: str,
        target: Template,
        target_tag: str,
        edge_type: Literal["refinement_of", "is_equal"],
    ):
        n1_id = self._add_node(source, tag=source_tag)
        n2_id = self._add_node(target, tag=target_tag)

        if edge_type == "refinement_of":
            # source is a refinement of target
            self.comparison_graph.add_edge(n1_id, n2_id, label=edge_type,
                                           color="red", weight=2)
        else:
            # is_equal: add edges both ways
            self.comparison_graph.add_edge(n1_id, n2_id, label=edge_type,
                                           color="red", weight=2)
            self.comparison_graph.add_edge(n2_id, n1_id, label=edge_type,
                                           color="red", weight=2)

    def _add_graphs(self):
        # Add the graphs together
        nodes_to_add = []
        template_node_ids = set()
        for node, node_data in self.templ1_graph.nodes(data=True):
            # If Template node, append tag to node id
            if "template_key" in node_data:
                # NOTE: if we want to merge Template nodes skip appending
                # the tag to the tuple
                node_id = (*node, self.tag1)
                template_node_ids.add(node)
            else:
                # Assumed to be a Concept node
                node_id = node
            node_data["color"] = self.tag1_color
            nodes_to_add.append((node_id, {"tags": {self.tag1}, **node_data}))

        self.comparison_graph.add_nodes_from(nodes_to_add)

        # For the other template, add nodes that are missing, update data
        # for the ones that are already in
        for node, node_data in self.templ2_graph.nodes(data=True):
            # NOTE: if we want to merge Template nodes skip appending
            # the tag to the tuple
            if "template_key" in node_data:
                node_id = (*node, self.tag2)
                template_node_ids.add(node)
                node_data["tags"] = {self.tag2}
                node_data["color"] = self.tag2_color
                self.comparison_graph.add_node(node_id, **node_data)
            else:
                if node in self.comparison_graph.nodes:
                    # If node already exists, add to tags and update color
                    self.comparison_graph.nodes[node]["tags"].add(self.tag2)
                    self.comparison_graph.nodes[node]["color"] = self.merge_color
                else:
                    # If node doesn't exist, add it
                    node_data["tags"] = {self.tag2}
                    node_data["color"] = self.tag2_color
                    self.comparison_graph.add_node(node, **node_data)

        self.comparison_graph.add_edges_from(
            ((*u, self.tag1) if u in template_node_ids else u,
             (*v, self.tag1) if v in template_node_ids else v,
             d)
            for u, v, d in self.templ1_graph.edges(data=True)
        )
        self.comparison_graph.add_edges_from(
            ((*u, self.tag2) if u in template_node_ids else u,
             (*v, self.tag2) if v in template_node_ids else v,
             d)
            for u, v, d in self.templ2_graph.edges(data=True)
        )

    def _assemble_comparison(self):
        self._add_graphs()

        for templ1, templ2 in product(self.template_model1.templates,
                                      self.template_model2.templates):
            # Check for refinement and equality
            if templ1.is_equal_to(templ2, with_context=True):
                self._add_edge(
                    source=templ1,
                    source_tag=self.tag1,
                    target=templ2,
                    target_tag=self.tag2,
                    edge_type="is_equal",
                )
            elif templ1.refinement_of(templ2,
                                      refinement_func=self.refinement_func,
                                      with_context=True):
                self._add_edge(
                    source=templ1,
                    source_tag=self.tag1,
                    target=templ2,
                    target_tag=self.tag2,
                    edge_type="refinement_of",
                )
            elif templ2.refinement_of(templ1,
                                      refinement_func=self.refinement_func,
                                      with_context=True):
                self._add_edge(
                    source=templ2,
                    source_tag=self.tag2,
                    target=templ1,
                    target_tag=self.tag1,
                    edge_type="refinement_of",
                )

    def draw_graph(
        self, path: str, prog: str = "dot", args: str = "", format: Optional[str] = None
    ):
        """Draw a pygraphviz graph of the differences using

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
            string. Example: "args="-Nshape=box -Edir=forward -Ecolor=red "
        """
        # draw graph
        agraph = nx.nx_agraph.to_agraph(self.comparison_graph)
        agraph.draw(path, format=format, prog=prog, args=args)

    def graph_as_json(self) -> Dict:
        """Return the comparison graph json serializable node-link data"""
        return nx.node_link_data(self.comparison_graph)


def get_concept_graph_key(concept: Concept):
    grounding_key = sorted(("identity", f"{k}:{v}")
                           for k, v in concept.identifiers.items()
                           if k != "biomodel.species")
    context_key = sorted(concept.context.items())
    key = [concept.name] + grounding_key + context_key
    key = tuple(key) if len(key) > 1 else (key[0],)
    return key


def get_template_graph_key(template: Template):
    name = template.type
    concept_keys = sorted(get_concept_graph_key(c) for c in
                          template.get_concepts())
    key = [name] + concept_keys
    return tuple(key) if len(key) > 1 else (key[0],)


class RefinementClosure:
    """A wrapper class for storing a transitive closure and exposing a
    function to check for refinement relationship.

    Typical usage would involve:
    >>> from mira.dkg.client import Neo4jClient
    >>> nc = Neo4jClient()
    >>> rc = RefinementClosure(nc.get_transitive_closure())
    >>> rc.is_ontological_child('doid:0080314', 'bfo:0000016')
    """
    def __init__(self, transitive_closure):
        self.transitive_closure = transitive_closure

    def is_ontological_child(self, child_curie: str, parent_curie: str) -> bool:
        return (child_curie, parent_curie) in self.transitive_closure


def main():
    """Generate the JSON schema file."""
    schema = get_json_schema()
    SCHEMA_PATH.write_text(json.dumps(schema, indent=2))


if __name__ == "__main__":
    main()
