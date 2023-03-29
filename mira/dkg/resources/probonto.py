import bioontologies
from collections import defaultdict
import itertools as itt
import rdflib
import json



def get_data_properties(rdf_graph, identifier):
    return {
        str(s).replace(
            "http://www.probonto.org/ontology#PROB_", "probonto:"
        ): str(o)
        for s, o in rdf_graph.subject_objects(
            rdflib.URIRef(f"http://www.probonto.org/ontology#PROB_{identifier}")
        )
    }


def get_instances(r, identifier):
    return [
        edge.sub
        for edge in r.edges
        if edge.pred == "rdf:type" and edge.obj == f"probonto:{identifier}"
    ]


def get_probonto_terms():
    r = (
        bioontologies.get_obograph_by_prefix("probonto")
        .guess("probonto")
        .standardize()
    )

    rdf_graph = rdflib.Graph()
    url = "https://raw.githubusercontent.com/probonto/ontology/master/probonto4ols.owl"
    rdf_graph.parse(url, format="ttl")

    labels = r.get_curie_to_name()

    # All distributions are individuals with a given type (http://www.probonto.org/ontology#PROB_c0000020)
    distributions = get_instances(r, "c0000020")

    # All parameters are annotated with a specific object property (i.e., predicate).
    distribution_to_parameters = defaultdict(list)
    for edge in r.edges:
        if edge.pred == "probonto:c0000062":
            distribution_to_parameters[edge.sub].append(edge.obj)
    distribution_to_parameters = dict(distribution_to_parameters)

    parameters = set(itt.chain.from_iterable(distribution_to_parameters.values()))

    node = next(node for node in r.nodes if node.luid == "k0000596")

    object_to_short_name = get_data_properties(rdf_graph, "c0000051")

    object_to_latex = get_data_properties(rdf_graph, "c0000031")

    from_distributions = {}
    to_distributions = {}
    for edge in r.edges:
        if edge.pred == "probonto:c0000071":
            from_distributions[edge.sub] = edge.obj
        elif edge.pred == "probonto:c0000072":
            to_distributions[edge.sub] = edge.obj

    same_distribution = defaultdict(list)
    for reparametrization in get_instances(r, "c0000065"):
        same_distribution[from_distributions[reparametrization]].append(
            to_distributions[reparametrization]
        )

    same_distribution = dict(same_distribution)

    results = []
    for distribution_curie, ps in distribution_to_parameters.items():
        v = {
            "curie": distribution_curie,
            "name": labels[distribution_curie],
            "equivalent": [
                {"curie": eq, "name": labels[eq]}
                for eq in same_distribution.get(distribution_curie, [])
            ],
        }
        parameters = []
        for p in ps:
            d = {
                "curie": p,
                "name": labels[p],
                "symbol": object_to_latex[p],
                "short_name": object_to_short_name.get(p)
                              or labels[p].split(" of ")[0],
            }
            parameters.append(d)
        v["parameters"] = parameters
        results.append(v)
    return results


def main():
    results = get_probonto_terms()
    with open("probonto.json", "w") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
