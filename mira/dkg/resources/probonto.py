import json
from collections import defaultdict

import bioontologies
import rdflib


def get_data_properties(rdf_graph: rdflib.Graph, identifier):
    return {
        str(s).replace(
            "http://www.probonto.org/ontology#PROB_", "probonto:"
        ): str(o).replace("\n", " ").replace("  ", " ")
        for s, o in rdf_graph.subject_objects(
            rdflib.URIRef(f"http://www.probonto.org/ontology#PROB_{identifier}")
        )
    }


def get_instances(obo_graph, probonto_identifier: str):
    return [
        edge.sub
        for edge in obo_graph.edges
        if edge.pred == "rdf:type" and edge.obj == f"probonto:{probonto_identifier}"
    ]


def get_probonto_terms():
    obo_graph = (
        bioontologies.get_obograph_by_prefix("probonto")
        .guess("probonto")
        .standardize()
    )

    rdf_graph = rdflib.Graph()
    url = "https://raw.githubusercontent.com/probonto/ontology/master/probonto4ols.owl"
    rdf_graph.parse(url, format="ttl")

    # ProbOnto uses a convention by which the code name is used to identify
    # distributions and their parameters with human-readable labels.
    labels = get_data_properties(rdf_graph, "c0000029")

    # As for parameters, the short code name is used to identify them.
    short_code_names = get_data_properties(rdf_graph, "c0000060")

    # All parameters are annotated with a specific object property (i.e., predicate).
    distribution_to_parameters = defaultdict(list)
    for edge in obo_graph.edges:
        if edge.pred == "probonto:c0000062":
            distribution_to_parameters[edge.sub].append(edge.obj)
    distribution_to_parameters = dict(distribution_to_parameters)

    object_to_short_name = get_data_properties(rdf_graph, "c0000051")

    object_to_latex = get_data_properties(rdf_graph, "c0000031")

    from_distributions = {}
    to_distributions = {}
    for edge in obo_graph.edges:
        if edge.pred == "probonto:c0000071":
            from_distributions[edge.sub] = edge.obj
        elif edge.pred == "probonto:c0000072":
            to_distributions[edge.sub] = edge.obj

    same_distribution = defaultdict(list)
    for reparametrization in get_instances(obo_graph, "c0000065"):
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
                "name": short_code_names[p],
                "symbol": object_to_latex[p],
                "short_name": object_to_short_name.get(p)
                or labels[p].replace("\n", " ").replace("  ", " ").split(" of ")[0],
            }
            parameters.append(d)
        v["parameters"] = parameters
        results.append(v)
    return results


def main():
    results = get_probonto_terms()
    with open("probonto.json", "w") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
