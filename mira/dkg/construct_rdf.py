"""Construct a lossy export of the MIRA DKG in RDF."""

import csv

import rdflib
from rdflib import Literal
from tqdm import tqdm

from mira.dkg.construct import DEMO_MODULE, EDGES_PATH, NODES_PATH, upload_s3

RDF_TTL_PATH = DEMO_MODULE.join(name="rdf.ttl")


def _ref(s: str):
    return rdflib.URIRef(f"https://bioregistry.io/{s}")


def main():
    """Create an RDF dump and upload to S3."""
    graph = rdflib.Graph()

    prefixes = {"bioregistry"}
    with NODES_PATH.open() as file:
        reader = csv.reader(file, delimiter="\t")
        _header = next(reader)
        it = tqdm(reader, unit="node", unit_scale=True)
        for curie, _label, name, synoynms, _obsolete, _type, description, xrefs, alts in it:
            if curie.startswith("_:geni"):
                continue
            prefix, identifier = curie.split(":", 1)
            prefixes.add(prefix)
            uri = _ref(curie)
            graph.add((uri, _ref("rdfs:label"), Literal(name)))
            graph.add((uri, _ref("rdfs:isDefinedBy"), _ref(f"bioregistry:{prefix}")))
            if description:
                graph.add((uri, _ref("dcterms:description"), Literal(description)))
            for synonym in synoynms.split(";"):
                if synonym:
                    graph.add((uri, _ref("skos.exactMatch"), Literal(synonym)))
            for xref in xrefs.split(";"):
                if xref:
                    graph.add((uri, _ref("owl.equivalentClass"), _ref(xref)))
                    prefixes.add(xref.split(":", 1)[0])
            for alt in alts.split(";"):
                if alt:
                    graph.add((uri, _ref("owl.equivalentClass"), _ref(alt)))

    prefixes.difference_update(prefix for prefix, _ in graph.namespaces())
    for prefix in prefixes:
        graph.bind(prefix, rdflib.Namespace(_ref(prefix) + ":"))

    with EDGES_PATH.open() as file:
        reader = csv.reader(file, delimiter="\t")
        _header = next(reader)
        it = tqdm(reader, unit="edge", unit_scale=True)
        for s, o, _type, p, _source, _graph in it:
            p_ref = rdflib.URIRef(p) if p.startswith("http") else _ref(p)
            graph.add((_ref(s), p_ref, _ref(o)))

    tqdm.write("serializing to turtle")
    graph.serialize(RDF_TTL_PATH, format="turtle")
    tqdm.write("done")

    upload_s3(RDF_TTL_PATH)


if __name__ == "__main__":
    main()
