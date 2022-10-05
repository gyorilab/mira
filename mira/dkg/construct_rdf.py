"""Construct a lossy export of the MIRA DKG in RDF."""

import csv
import gzip

import click
import rdflib
from rdflib import DC, DCTERMS, FOAF, OWL, RDF, RDFS, SKOS, Literal
from tqdm import tqdm

from mira.dkg.construct import DEMO_MODULE, EDGES_PATH, NODES_PATH, upload_s3

RDF_TTL_PATH = DEMO_MODULE.join(name="dkg.ttl.gz")

NAMESPACES = {
    "owl": OWL,
    "dc": DC,
    "dcterms": DCTERMS,
    "rdf": RDF,
    "rdfs": RDFS,
    "skos": SKOS,
    "foaf": FOAF,
}


def _ref(s: str):
    prefix, identifier = s.split(":", 1)
    namespace = NAMESPACES.get(prefix)
    if namespace:
        return namespace[identifier]
    return rdflib.URIRef(f"https://bioregistry.io/{s}")


def _construct_rdf(upload: bool):
    graph = rdflib.Graph()

    prefixes = {"bioregistry"}
    with gzip.open(NODES_PATH, "rt") as file:
        reader = csv.reader(file, delimiter="\t")
        _header = next(reader)
        it = tqdm(reader, unit="node", unit_scale=True)
        for (
            curie,
            _label,
            name,
            synoynms,
            _obsolete,
            _type,
            description,
            xrefs,
            alts,
            version,
            _property_predicates,  # TODO do something with these
            _property_values,
        ) in it:
            if not curie or curie.startswith("_:geni"):
                continue
            prefix, identifier = curie.split(":", 1)
            prefixes.add(prefix)
            try:
                uri = _ref(curie)
            except AttributeError as e:
                tqdm.write(f"Error on {curie}: {e} from ")
                continue
            if name:
                graph.add((uri, _ref("rdfs:label"), Literal(name)))
            graph.add((uri, _ref("rdfs:isDefinedBy"), _ref(f"bioregistry:{prefix}")))
            if version:
                graph.add((uri, DCTERMS.hasVersion, Literal(version)))
            if description:
                graph.add((uri, _ref("dcterms:description"), Literal(description)))
            for synonym in synoynms.split(";"):
                if synonym:
                    graph.add((uri, _ref("skos:exactMatch"), Literal(synonym)))
            for xref in xrefs.split(";"):
                if xref:
                    graph.add((uri, _ref("oboinowl:hasDbXref"), _ref(xref)))
                    prefixes.add(xref.split(":", 1)[0])
            for alt in alts.split(";"):
                if alt:
                    graph.add((uri, _ref("iao:0000118"), _ref(alt)))

    # prefixes.difference_update(prefix for prefix, _ in graph.namespaces())
    for prefix in prefixes:
        if prefix not in NAMESPACES:
            graph.bind(prefix, rdflib.Namespace(f"https://bioregistry.io/{prefix}:"))

    with gzip.open(EDGES_PATH, "rt") as file:
        reader = csv.reader(file, delimiter="\t")
        _header = next(reader)
        it = tqdm(reader, unit="edge", unit_scale=True)
        for s, o, _type, p, _source, _graph, _version in it:
            if s.startswith("http"):
                continue  # skip unnormalized
            p_ref = rdflib.URIRef(p) if p.startswith("http") else _ref(p)
            graph.add((_ref(s), p_ref, _ref(o)))

    tqdm.write("serializing to turtle")
    with gzip.open(RDF_TTL_PATH, "wb") as file:
        graph.serialize(file, format="turtle")
    tqdm.write("done")

    if upload:
        upload_s3(RDF_TTL_PATH)


@click.command()
@click.option("--upload", is_flag=True)
def main(upload: bool):
    """Create an RDF dump and upload to S3."""
    _construct_rdf(upload)


if __name__ == "__main__":
    main()
