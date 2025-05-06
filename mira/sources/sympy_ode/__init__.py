__all__ = ['template_model_from_sympy_odes']

import itertools
import logging

import sympy
from sympy import Function, Derivative, Eq, Expr

from mira.metamodel import *


logger = logging.getLogger(__name__)


def make_concept(name, data=None):
    concept_data = data.get(name, {}) if data else {}
    return Concept(name=name, **concept_data)


def make_param(name, data=None):
    param_data = data.get(name, {}) if data else {}
    return Parameter(name=name, **param_data)


class Hyperedge:
    def __init__(self, sources, targets, data):
        self.sources = sources if sources else set()
        self.targets = targets if targets else set()
        self.data = data

    def __str__(self):
        return '({%s}, {%s})' % (sorted(set(self.sources)),
                                 sorted(set(self.targets)))

    def __repr__(self):
        return str(self)


class Hypergraph:
    def __init__(self, nodes=None, edges=None):
        self.nodes = nodes if nodes else {}
        self.edges = edges if edges else {}

    def add_node(self, key, data):
        self.nodes[key] = data

    def add_edge(self, key, sources, targets, data=None):
        self.edges[key] = Hyperedge(sources, targets, data)
        for node in sources | targets:
            if node not in self.nodes:
                self.nodes[node] = {}

    def remove_edge(self, key):
        if key in self.edges:
            self.edges.pop(key)

    def in_degree(self, node):
        return sum([1 for edge in self.edges.values()
                    if node in edge.targets])

    def out_degree(self, node):
        return sum([1 for edge in self.edges.values()
                    if node in edge.sources])

    def in_edges(self, node):
        return {key for key, edge in self.edges
                if node in edge.targets}

    def out_edges(self, node):
        return {key for key, edge in self.edges.items()
                if node in edge.sources}

    def get_connected_nodes(self):
        connected_nodes = set()
        for node in self.nodes:
            if self.out_degree(node) or self.in_degree(node):
                connected_nodes.add(node)
        return connected_nodes

    def get_unconnected_nodes(self):
        return set(self.nodes) - self.get_connected_nodes()

    def remove_ambiguous_edges(self):
        # Initialize a matching and a set of covered nodes
        matching = {}
        covered_nodes = set()

        # Iterate over the edges in the hypergraph and add them to the matching
        # if they do not cover any previously covered nodes
        for key, edge in self.edges.items():
            edge_nodes = edge.sources | edge.targets
            # If any node in this edge is already covered by a previously chosen edge, skip it.
            if covered_nodes & edge_nodes:
                continue
            # Otherwise, add the edge to our matching.
            matching[key] = edge
            covered_nodes.update(edge_nodes)

        # Remove hyperedges that are not in the matching
        keys_to_remove = set(self.edges.keys()) - set(matching.keys())
        for key in keys_to_remove:
            self.remove_edge(key)


def template_model_from_sympy_odes(odes, concept_data=None, param_data=None):
    """Return a TemplateModel from a set of sympy ODEs.

    Parameters
    ----------
    odes : list of sympy.Eq
        A list of sympy equations representing the ODEs.
        example input: odes = [Eq(Derivative(S(t), t), -b*I(t)*S(t)),
         Eq(Derivative(E(t), t), b*I(t)*S(t) - r*E(t)),
         Eq(Derivative(I(t), t), -g*I(t) + r*E(t)),
         Eq(Derivative(R(t), t), g*I(t))]
    concept_data : Optional[dict]
        An optional dictionary of data used when constructing
        concepts. The keys are the names of the concepts and the
        values are dictionaries of data to pass to the Concept
        constructor.
    param_data : Optional[dict]
        An optional dictionary of data used when constructing
        parameters. The keys are the names of the parameters and
        the values are dictionaries of data to pass to the Parameter
        constructor.

    Returns
    -------
    : TemplateModel
        A template model representing the ODEs.
    """
    concept_data = concept_data or {}
    param_data = param_data or {}
    variables = []
    time_variables = set()

    # Step 1: consistency checks
    for ode in odes:
        if not isinstance(ode, Eq):
            raise ValueError(f"ODE {ode} is not an equation")
        if not isinstance(ode.lhs, Derivative):
            raise ValueError(f"ODE {ode} does not have a derivative on the left-hand side")
        if not isinstance(ode.lhs.args[0], Function):
            raise ValueError(f"ODE {ode} does not have a function on the left-hand side")
        if not isinstance(ode.rhs, Expr):
            raise ValueError(f"ODE {ode} does not have an expression on the right-hand side")
        time_variables.add(ode.lhs.args[1][0])
        if len(time_variables) > 1:
            raise ValueError("Multiple time variables in the ODEs")
    time_variable = time_variables.pop()

    # Step 2: determine LHS variables and handle static concepts
    is_static = set()
    for ode in odes:
        lhs_fun = ode.lhs.args[0]
        variable_name = lhs_fun.name
        variables.append(variable_name)
        if ode.rhs == 0:
            is_static.add(variable_name)

    # Step 3: Interpret RHS equations and build a hypergraph
    parameters = set()
    all_terms = []
    G = Hypergraph()
    for lhs_variable, eq in zip(variables, odes):
        # No terms to add for static variables
        if lhs_variable in is_static:
            continue
        # Break up the RHS into a sum of terms
        terms = eq.rhs.as_ordered_terms()
        for term_idx, term in enumerate(terms):
            # Check if the term is negated
            neg = is_negative(term, time_variable)
            # Extract term parameters and keep track in a set
            parameters |= term.free_symbols - {time_variable}
            # Determine potential controllers of the term
            funcs = term.atoms(Function)
            # Potential controllers are all variables in the term
            # that are not the LHS variable
            potential_controllers = \
                ({f.name for f in funcs if hasattr(f, 'name')}
                 & set(variables)) - {lhs_variable}
            # Now we add the term as a node to the hypergraph with some
            # further properties needed later
            G.add_node((lhs_variable, term_idx),
                       {'neg': neg, 'term': term, 'lhs_var': lhs_variable,
                        'potential_controllers': potential_controllers})
    logger.debug("Constructed hypergraph with %d nodes", len(G.nodes))

    # Precompute and store expanded forms
    expr_map = {}
    for node in G.nodes:
        term = sympy.expand(G.nodes[node]['term'])
        expr_map[node] = term

    # First, we look at all pairs of terms and check if the terms are
    # compatible, in which case we add a hyperedge between them
    edge_idx = 0
    for n1, n2 in itertools.combinations(G.nodes, 2):
        if expr_map[n1] + expr_map[n2] == 0:
            sources = {n1 if G.nodes[n1]['neg'] else n2}
            targets = {n1, n2} - sources
            G.add_edge(edge_idx, sources, targets)
            edge_idx += 1

    # Next we look at all 3-sets of terms and see if they form an equation
    # in which case we add a hyperedge between the two sides
    for n1, n2, n3 in itertools.combinations(G.get_unconnected_nodes(), 3):
        nodes = {n1, n2, n3}
        if expr_map[n1] + expr_map[n2] + expr_map[n3] == 0:
            sources = {n for n in nodes if G.nodes[n]['neg']}
            targets = nodes - sources
            G.add_edge(edge_idx, sources, targets)

    # Remove ambiguous edges
    G.remove_ambiguous_edges()

    templates = []

    # We first handle static concepts
    for variable in is_static:
        concept = make_concept(variable, concept_data)
        templates.append(StaticConcept(subject=concept))

    # We next look at unconnected nodes of the graph and construct
    # production or degradation templates
    for node in G.get_unconnected_nodes():
        data = G.nodes[node]
        term = data['term']
        rate_law = term.subs({f: sympy.Symbol(f.name)
                              for f in term.atoms(Function)
                              if hasattr(f, 'name') and f.name in variables})
        concept = make_concept(data['lhs_var'], concept_data)
        controllers = data['potential_controllers'] - {data['lhs_var']}
        if data['neg']:
            rate_law = -rate_law
            if not controllers:
                template = NaturalDegradation(subject=concept,
                                              rate_law=rate_law)
            elif len(controllers) == 1:
                contr_concept = make_concept(controllers.pop(), concept_data)
                template = ControlledDegradation(subject=concept,
                                                 controller=contr_concept,
                                                 rate_law=rate_law)
            else:
                controller_concepts = [make_concept(c, concept_data)
                                       for c in controllers]
                template = GroupedControlledDegradation(
                    subject=concept, controllers=controller_concepts,
                    rate_law=rate_law)
        else:
            if not controllers:
                template = NaturalProduction(outcome=concept,
                                             rate_law=rate_law)
            elif len(controllers) == 1:
                contr_concept = make_concept(controllers.pop(), concept_data)
                template = ControlledProduction(outcome=concept,
                                                controller=contr_concept,
                                                rate_law=rate_law)
            else:
                controller_concepts = [make_concept(c, concept_data)
                                       for c in controllers]
                template = GroupedControlledProduction(
                    outcome=concept, controllers=controller_concepts,
                    rate_law=rate_law)
        templates.append(template)

    # Next, we look at edges in the graph and construct conversion
    # templates from these
    for edge in G.edges.values():
        all_potential_controllers = set()
        for node in edge.sources | edge.targets:
            all_potential_controllers |= G.nodes[node]['potential_controllers']
        controllers = all_potential_controllers - \
            {G.nodes[s]['lhs_var'] for s in edge.sources}
        controller_concepts = [make_concept(c, concept_data)
                               for c in controllers]
        # Sources are consumed
        source_concepts = {s: make_concept(G.nodes[s]['lhs_var'], concept_data)
                           for s in edge.sources}
        target_concepts = {t: make_concept(G.nodes[t]['lhs_var'], concept_data)
                           for t in edge.targets}
        for source, target in itertools.product(edge.sources, edge.targets):
            source_concept = source_concepts[source]
            target_concept = target_concepts[target]
            term = G.nodes[target]['term']
            rate_law = (term.subs({f: sympy.Symbol(f.name)
                        for f in term.atoms(Function)}))
            if not controllers:
                template = NaturalConversion(subject=source_concept, outcome=target_concept,
                                             rate_law=rate_law)
            elif len(controllers) == 1:
                template = ControlledConversion(subject=source_concept, outcome=target_concept,
                                                controller=list(controller_concepts)[0],
                                                rate_law=rate_law)
            else:
                template = GroupedControlledConversion(
                    subject=source_concept, outcome=target_concept,
                    controllers=controller_concepts,
                    rate_law=rate_law)
            templates.append(template)

    # Compile parameter symbols for the template model
    params = {p.name: make_param(name=p.name, data=param_data)
              for p in parameters}
    # Instantiate the time variable
    time = Time(name=time_variable.name)

    # Construct the template model
    tm = TemplateModel(templates=templates, parameters=params,
                       time=time)
    return tm


def is_negative(term, time):
    # Replace any parameters with 0.1, assuming positivity
    term = term.subs({s: 0.1 for s in term.free_symbols
                      if s != time})
    # Now look at the variables appearing in the term and differentiate
    funcs = term.atoms(Function)
    for func in funcs:
        # Replace the function with 1, assuming positivity
        term = term.subs(func, 1)
    # Whatever is left is the ultimate sign of the term with respect
    # to its variables
    return term.is_negative
