__all__ = ["ModelComparisonGraphdata", "TemplateModelComparison",
           "TemplateModelDelta", "RefinementClosure",
           "get_dkg_refinement_closure"]

from collections import defaultdict
from itertools import combinations, count, product
from typing import Literal, Optional, Mapping, List, Tuple, Dict, Callable, \
    Union

import networkx as nx
import sympy
from pydantic import BaseModel, conint, Field
from tqdm import tqdm

from .templates import Provenance, Concept, Template, SympyExprStr, IS_EQUAL, \
    REFINEMENT_OF, CONTROLLER, CONTROLLERS, SUBJECT, OUTCOME, SpecifiedTemplate
from .template_model import Initial, TemplateModel, get_concept_graph_key, \
    get_template_graph_key
from .utils import safe_parse_expr


class DataNode(BaseModel):
    """A node in a ModelComparisonGraphdata"""

    node_type: Literal["template", "concept"]
    model_id: conint(ge=0, strict=True)


class TemplateNode(DataNode):
    """A node in a ModelComparisonGraphdata representing a Template"""

    type: str
    rate_law: Optional[SympyExprStr] = \
        Field(default=None, description="The rate law of this template")
    initials: Optional[Mapping[str, Initial]] = \
        Field(default=None, description="The initial conditions associated "
                                        "with the rate law for this template")
    provenance: List[Provenance] = Field(default_factory=list)


class ConceptNode(Concept, DataNode):
    """A node in a ModelComparisonGraphdata representing a Concept"""

    curie: str


DataNodeKey = Tuple[str, ...]


class DataEdge(BaseModel):
    """An edge in a ModelComparisonGraphdata"""

    source_id: DataNodeKey
    target_id: DataNodeKey


class InterModelEdge(DataEdge):
    role: Literal["refinement_of", "is_equal"]


class IntraModelEdge(DataEdge):
    role: Literal["subject", "outcome", "controller"]


class ModelComparisonGraphdata(BaseModel):
    """A data structure holding a graph representation of TemplateModel delta"""
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            SympyExprStr: lambda e: str(e),
        }
        json_decoders = {
            SympyExprStr: lambda e: safe_parse_expr(e),
            Template: lambda t: Template.from_json(data=t),
        }

    template_models: Dict[int, TemplateModel] = Field(
        ..., description="A mapping of template model keys to template models"
    )
    concept_nodes: Dict[int, Dict[int, Concept]] = Field(
        default_factory=list,
        description="A mapping of model identifiers to a mapping of node "
        "identifiers to nodes. Node identifiers have the structure of 'mXnY' "
        "where X is the model id and Y is the node id within the model.",
    )
    template_nodes: Dict[int, Dict[int, SpecifiedTemplate]] = Field(
        default_factory=list,
        description="A mapping of model identifiers to a mapping of node "
        "identifiers to nodes. Node identifiers have the structure of 'mXnY' "
        "where X is the model id and Y is the node id within the model.",
    )
    # nodes are tuples of (model id, node id) for look
    inter_model_edges: List[Tuple[Tuple[int, int], Tuple[int, int], str]] = \
        Field(
        default_factory=list,
        description="List of edges. Each edge is a tuple of"
        "(source node lookup, target node lookup, role) where role describes "
        "if the edge is a refinement of or equal to another node in another "
        "model (inter model edge). The edges are considered directed for "
        "refinements and undirected for equalities. The node lookup is a "
        "tuple of (model id, node id) that defines the lookup of the node "
        "in the nodes mapping.",
    )
    intra_model_edges: List[Tuple[Tuple[int, int], Tuple[int, int], str]] = Field(
        default_factory=list,
        description="List of edges. Each edge is a tuple of"
        "(source node lookup, target node lookup, role) where role describes "
        "if the edge incoming to, outgoing from or controls a "
        "template/process in the same model (intra model edge). The edges "
        "are considered directed. The node lookup is a tuple of "
        "(model id, node id) that defines the lookup of the node in the "
        "nodes mapping.",
    )

    def get_similarity_score(self, model1_id: int, model2_id: int) -> float:
        """Get the similarity score of the model comparison"""

        # Get all concept nodes for each model
        model1_concept_nodes = set()
        for node_id, node in self.concept_nodes[model1_id].items():
            model1_concept_nodes.add((model1_id, node_id))
        model2_concept_nodes = set()
        for node_id, node in self.concept_nodes[model2_id].items():
            model2_concept_nodes.add((model2_id, node_id))

        # Check which model has the most nodes
        n_nodes1 = len(model1_concept_nodes)
        n_nodes2 = len(model2_concept_nodes)

        # Set model 1 to be the model with the most nodes
        if n_nodes2 > n_nodes1:
            # Switch the sets
            model1_concept_nodes, model2_concept_nodes = \
                model2_concept_nodes, model1_concept_nodes
            # Switch the number of nodes
            n_nodes2, n_nodes1 = n_nodes1, n_nodes2
            # Switch the model ids
            model1_id, model2_id = model2_id, model1_id

        # Create an index of all the edges between the two models
        index = defaultdict(lambda: defaultdict(set))
        for t in (IS_EQUAL, REFINEMENT_OF):
            for (msource_id, source_id), (mtarget_id, target_id), e_type in \
                    self.inter_model_edges:
                source_tuple = (msource_id, source_id)
                target_tuple = (mtarget_id, target_id)
                if e_type != t:
                    continue

                # Add model1 -> model2 edge
                if msource_id == model1_id and mtarget_id == model2_id:
                    index[t][source_tuple].add(target_tuple)
                # Add model2 -> model1 edge
                if msource_id == model2_id and mtarget_id == model1_id:
                    index[t][target_tuple].add(source_tuple)

        score = 0
        for model1_node_json in model1_concept_nodes:
            if model1_node_json in index[IS_EQUAL]:
                # todo: fix this check
                score += 1
            elif model1_node_json in index[REFINEMENT_OF]:
                score += 0.5

        # Todo: Come up with a better metric?
        concept_similarity_score = score / n_nodes1

        return concept_similarity_score

    def get_similarity_scores(self):
        """Get the similarity scores for all model comparisons"""
        scores = []
        for i, j in combinations(range(len(self.template_models)), 2):
            scores.append({
                'models': (i,j),
                'score': self.get_similarity_score(i, j)
            })
        return scores

    @classmethod
    def from_template_models(
            cls,
            template_models: List[TemplateModel],
            refinement_func: Callable[[str, str], bool]
    ) -> "ModelComparisonGraphdata":
        return TemplateModelComparison(
            template_models, refinement_func
        ).model_comparison


class TemplateModelComparison:
    """Compares TemplateModels in a graph friendly structure"""
    model_comparison: ModelComparisonGraphdata

    def __init__(
        self,
        template_models: List[TemplateModel],
        refinement_func: Callable[[str, str], bool]
    ):
        # Todo: Add more identifiable ID to template model than index?
        if len(template_models) < 2:
            raise ValueError("Need at least two models to make comparison")
        self.template_node_lookup: Dict[Tuple, Template] = {}
        self.concept_node_lookup: Dict[Tuple, Concept] = {}
        self.intra_model_edges: List[Tuple[Tuple, Tuple, str]] = []
        self.inter_model_edges: List[Tuple[Tuple, Tuple, str]] = []
        self.refinement_func = refinement_func
        self.template_models: Dict[int, TemplateModel] = {
            ix: tm for ix, tm in enumerate(iterable=template_models)
        }
        self.compare_models()

    def _add_concept_nodes_edges(
            self,
            template_node_id: Tuple,
            role: str,
            concept: Union[Concept, List[Concept]]):
        model_id = template_node_id[0]
        # Add one or several concept nodes with their template-concept edges
        if isinstance(concept, Concept):
            # Just need some hashable id for the concept and then translate
            # it to an integer
            concept_node_id = (model_id,) + get_concept_graph_key(concept)
            if concept_node_id not in self.concept_node_lookup:
                self.concept_node_lookup[concept_node_id] = concept

            # Add edges for subjects, controllers and outcomes
            if role in [CONTROLLER, CONTROLLERS, SUBJECT]:
                self.intra_model_edges.append(
                    (concept_node_id, template_node_id, role)
                )
            elif role == OUTCOME:
                self.intra_model_edges.append(
                    (template_node_id, concept_node_id, role)
                )
            else:
                raise ValueError(f"Invalid role {role}")
        elif isinstance(concept, list):
            for conc in concept:
                self._add_concept_nodes_edges(
                    template_node_id, role, conc
                )
        else:
            raise TypeError(f"Invalid concept type {type(concept)}")

    def _add_template_model(
            self, model_id: int, template_model: TemplateModel
    ):
        # Create the graph data for this template model
        for template in template_model.templates:
            template_node_id = (model_id, ) + get_template_graph_key(template)
            if template_node_id not in self.template_node_lookup:
                self.template_node_lookup[template_node_id] = template

            # Add concept nodes and intra model edges
            for role, concept in template.get_concepts_by_role().items():
                self._add_concept_nodes_edges(template_node_id, role, concept)

    def _add_inter_model_edges(
        self,
        node_id1: Tuple[str, ...],
        data_node1: Union[Concept, Template],
        node_id2: Tuple[str, ...],
        data_node2: Union[Concept, Template],
    ):
        if data_node1.is_equal_to(data_node2, with_context=True):
            # Add equality edge
            self.inter_model_edges.append(
                (node_id1, node_id2, "is_equal")
            )
        elif data_node1.refinement_of(data_node2, self.refinement_func, with_context=True):
            self.inter_model_edges.append(
                (node_id1, node_id2, "refinement_of")
            )
        elif data_node2.refinement_of(data_node1, self.refinement_func, with_context=True):
            self.inter_model_edges.append(
                (node_id2, node_id1, "refinement_of")
            )

    def compare_models(self):
        """Compare TemplateModels and return a graph of the differences"""
        for model_id, template_model in self.template_models.items():
            self._add_template_model(model_id, template_model)

        # Create inter model edges, i.e refinements and equalities
        for (node_id1, data_node1), (node_id2, data_node2) in \
                tqdm(combinations(self.template_node_lookup.items(), r=2),
                     desc="Comparing model templates"):
            if node_id1[:2] == node_id2[:2]:
                continue
            self._add_inter_model_edges(node_id1, data_node1,
                                        node_id2, data_node2)

        # Create inter model edges, i.e refinements and equalities
        for (node_id1, data_node1), (node_id2, data_node2) in \
                tqdm(combinations(self.concept_node_lookup.items(), r=2),
                     desc="Comparing model concepts"):
            if node_id1[:2] == node_id2[:2]:
                continue
            self._add_inter_model_edges(node_id1, data_node1,
                                        node_id2, data_node2)

        concept_nodes = defaultdict(dict)
        template_nodes = defaultdict(dict)
        model_node_counters = {}
        old_new_map = {}
        for old_node_id, node in self.template_node_lookup.items():
            m_id = old_node_id[0]

            # Restart node counter for new models
            if m_id not in model_node_counters:
                model_node_counter = count()
                model_node_counters[m_id] = model_node_counter
            else:
                model_node_counter = model_node_counters[m_id]

            node_id = next(model_node_counter)
            old_new_map[old_node_id] = (m_id, node_id)
            template_nodes[m_id][node_id] = node

        for old_node_id, node in self.concept_node_lookup.items():
            m_id = old_node_id[0]

            # Restart node counter for new models
            if m_id not in model_node_counters:
                model_node_counter = count()
                model_node_counters[m_id] = model_node_counter
            else:
                model_node_counter = model_node_counters[m_id]

            node_id = next(model_node_counter)
            old_new_map[old_node_id] = (m_id, node_id)
            concept_nodes[m_id][node_id] = node

            # todo: consider doing nested arrays instead of nested mappings
            #  for both nodes and models
            # nodes: [
            #           [{node}, ...],
            #           [{node}, ...],
            #       ]

        # translate old node ids to new node ids in the edges
        inter_model_edges = [
            (old_new_map[old_node_id1], old_new_map[old_node_id2], edge_type)
            for old_node_id1, old_node_id2, edge_type in self.inter_model_edges
        ]
        intra_model_edges = [
            (old_new_map[old_node_id1], old_new_map[old_node_id2], edge_type)
            for old_node_id1, old_node_id2, edge_type in self.intra_model_edges
        ]
        self.model_comparison = ModelComparisonGraphdata(
            template_models=self.template_models,
            template_nodes=template_nodes,
            concept_nodes=concept_nodes,
            inter_model_edges=inter_model_edges,
            intra_model_edges=intra_model_edges
        )


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
        self.comparison_graph = nx.DiGraph()
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

        model1_identity_keys = {
            data['concept_identity_key']: node for node, data
            in self.templ1_graph.nodes(data=True)
            if 'concept_identity_key' in data
        }

        to_contract = set()

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
                # There is an exact match for this node so we don't need
                # to add it
                if node in self.comparison_graph.nodes:
                    # If node already exists, add to tags and update color
                    self.comparison_graph.nodes[node]["tags"].add(self.tag2)
                    self.comparison_graph.nodes[node]["color"] = self.merge_color
                # There is an identity match but tha names (unstandardized)
                # don't match. So we merge these nodes later
                elif node_data['concept_identity_key'] in model1_identity_keys:
                    # Make sure the color will be the merge color
                    matching_node = model1_identity_keys[node_data['concept_identity_key']]
                    self.comparison_graph.nodes[matching_node]["color"] = self.merge_color
                    # We still add the node, it will be contracted later
                    node_data["tags"] = {self.tag2}
                    node_data["color"] = self.merge_color
                    self.comparison_graph.add_node(node, **node_data)
                    # Add to the list of contracted nodes
                    to_contract.add((node, matching_node))
                # There is no match so we add a new node
                else:
                    # If node doesn't exist, add it
                    node_data["tags"] = {self.tag2}
                    node_data["color"] = self.tag2_color
                    self.comparison_graph.add_node(node, **node_data)

        def extend_data(d, color):
            d["color"] = color
            return d

        self.comparison_graph.add_edges_from(
            ((*u, self.tag1) if u in template_node_ids else u,
             (*v, self.tag1) if v in template_node_ids else v,
             extend_data(d, self.tag1_color))
            for u, v, d in self.templ1_graph.edges(data=True)
        )
        self.comparison_graph.add_edges_from(
            ((*u, self.tag2) if u in template_node_ids else u,
             (*v, self.tag2) if v in template_node_ids else v,
             extend_data(d, self.tag2_color))
            for u, v, d in self.templ2_graph.edges(data=True)
        )

        # Add lookup of concepts so we can add refinement edges
        templ1_concepts = {}
        for templ1 in self.template_model1.templates:
            for concept in templ1.get_concepts():
                key = get_concept_graph_key(concept)
                templ1_concepts[key] = concept
        templ2_concepts = {}
        for templ2 in self.template_model2.templates:
            for concept in templ2.get_concepts():
                key = get_concept_graph_key(concept)
                templ2_concepts[key] = concept

        concept_refinement_edges = []
        joint_concept_keys = set().union(templ1_concepts.keys()).union(templ2_concepts.keys())
        ref_dict = dict(label="refinement_of", color="red", weight=2)
        for (n_a, data_a), (n_b, data_b) in combinations(self.comparison_graph.nodes(data=True), 2):
            if n_a in joint_concept_keys and n_b in joint_concept_keys:
                if self.tag1 in data_a["tags"]:
                    c1 = templ1_concepts[n_a]
                elif self.tag1 in data_b["tags"]:
                    c1 = templ1_concepts[n_b]
                else:
                    continue

                if self.tag2 in data_a["tags"]:
                    c2 = templ2_concepts[n_a]
                elif self.tag2 in data_b["tags"]:
                    c2 = templ2_concepts[n_b]
                else:
                    continue
                if c1.is_equal_to(c2, with_context=True):
                    continue
                if c1.refinement_of(c2,
                                    refinement_func=self.refinement_func,
                                    with_context=True):
                    concept_refinement_edges.append((n_a, n_b, ref_dict))
                if c2.refinement_of(c1,
                                    refinement_func=self.refinement_func,
                                    with_context=True):
                    concept_refinement_edges.append((n_b, n_a, ref_dict))

        if concept_refinement_edges:
            self.comparison_graph.add_edges_from(concept_refinement_edges)

        for u, v in to_contract:
            self.comparison_graph = \
                nx.contracted_nodes(self.comparison_graph, u, v)

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

    @classmethod
    def for_jupyter(
            cls,
            template_model1,
            template_model2,
            refinement_function,
            name="model.png",
            tag1="1",
            tag2="2",
            tag1_color="blue",
            tag2_color="green",
            merge_color="orange",
            prog: str = "dot",
            args: str = "",
            format: Optional[str] = None,
            **kwargs
    ):
        """Display in jupyter

        Parameters
        ----------
        template_model1 :
            The first template model
        template_model2 :
            The second template model
        refinement_function :
            The refinement function to use
        name :
            The name of the output file
        tag1 :
            The tag for the first template model
        tag2 :
            The tag for the second template model
        tag1_color :
            The color for the first template model
        tag2_color :
            The color for the second template model
        merge_color :
            The color for the merged template model
        prog :
            The graphviz layout program to use, such as "dot", "neato", etc.
        format :
            Set the file format explicitly
        args :
            Additional arguments to pass to the graphviz bash program as a
            string. Example: "args="-Nshape=box -Edir=forward -Ecolor=red"
        kwargs :
            Keyword arguments to pass to IPython.display.Image
        """
        from IPython.display import Image

        if not name.endswith(".png"):
            name += ".png"
            print(f"Appending .png to name. New name: {name}")

        TemplateModelDelta(template_model1=template_model1,
                           template_model2=template_model2,
                           refinement_function=refinement_function,
                           tag1=tag1,
                           tag2=tag2,
                           tag1_color=tag1_color,
                           tag2_color=tag2_color,
                           merge_color=merge_color
                           ).draw_graph(name,
                                        prog=prog,
                                        args=args,
                                        format=format)

        return Image(name, **kwargs)


class RefinementClosure:
    """A wrapper class for storing a transitive closure and exposing a
    function to check for refinement relationship.

    Typical usage would involve:
    >>> from mira.dkg.web_client import get_transitive_closure_web
    >>> rc = RefinementClosure(get_transitive_closure_web())
    >>> rc.is_ontological_child('doid:0080314', 'bfo:0000016')
    """
    def __init__(self, transitive_closure):
        self.transitive_closure = transitive_closure

    def is_ontological_child(self, child_curie: str, parent_curie: str) -> bool:
        return (child_curie, parent_curie) in self.transitive_closure


def get_dkg_refinement_closure():
    """Return a refinement closure from the DKG"""
    # Import here to avoid dependency upon module import
    from mira.dkg.web_client import get_transitive_closure_web
    rc = RefinementClosure(get_transitive_closure_web())
    return rc
