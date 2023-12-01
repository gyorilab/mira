import curies
import pystow
from curies import Converter
from pathlib import Path
from pyobo import Term, Reference, TypeDef
import bioregistry

MODULE = pystow.module("mira", "extract_eiffel")
ECV_KB_URL = (
    "https://raw.githubusercontent.com/benmomo/"
    "eiffel-ontology/main/ontology/ecv-kb.ttl"
)
EO_KB_URL = (
    "https://raw.githubusercontent.com/benmomo/"
    "eiffel-ontology/main/ontology/eo-kb.ttl"
)
SDG_SERIES_URL = (
    "https://raw.githubusercontent.com/benmomo/eiffel"
    "-ontology/main/ontology/sdg-kos-series-2019-Q2-G-01.ttl"
)
SDG_GOAL_URL = (
    "https://raw.githubusercontent.com/benmomo/eiffel-ontology/"
    "main/ontology/sdg-kos-goals-targets-indicators.ttl"
)

ECV_INFO_QUERY = """
SELECT DISTINCT ?individual ?description ?label
WHERE {
    ?individual rdf:type ?type .
    ?individual rdfs:label ?label .
    OPTIONAL { ?individual dc:description ?description } .
    FILTER (?individual != <http://purl.org/eiffo/ecv>) . 
}
"""

ECV_RELATION_QUERY = """
SELECT ?subject ?predicate ?object ?label
WHERE{
    { ?subject ?predicate ?object }. 
    ?subject rdfs:label ?label 
    FILTER (isIRI(?object) && (CONTAINS(STR(?predicate), "ecv")))
}
"""

EO_INFO_QUERY = """
SELECT DISTINCT ?individual ?type ?description ?label
WHERE {
    {   
    ?individual rdf:type ?type.
    ?individual rdfs:label ?label.
    OPTIONAL{ ?individual dc:description ?description } .
    }   
UNION
    {
    ?individual rdf:type :Area .
    ?individual rdfs:label ?label .
    ?individual :areaKeyWords ?description .
    }
    FILTER (?individual != <http:/purl.org/eiffo/eotaxonomy>) .
}

"""
EO_RELATION_QUERY = """
SELECT ?subject ?predicate ?object ?label
WHERE{
    { ?subject ?predicate ?object }. 
    ?subject rdfs:label ?label 
    FILTER (isIRI(?object) && (CONTAINS(STR(?predicate), "eotaxonomy")))
}
"""

SDG_INFO_QUERY = """
SELECT DISTINCT ?individual ?label
WHERE {
    ?individual skos:prefLabel ?label.
    FILTER(LANG(?label) = 'en' && ?individual != <http://metadata.un.org/sdg>)
}
"""

SDG_GOALS_RELATION_QUERY = """
SELECT ?subject ?predicate ?object ?label
WHERE{
    { ?subject ?predicate ?object }. 
    ?subject skos:prefLabel ?label .  
    FILTER (LANG(?label) = 'en' && ?predicate NOT IN (skos:inScheme, 
        skos:exactMatch, sdgo:tier, skos:topConceptOf, skos:hasTopConcept) && 
        isIRI(?object) && (CONTAINS(STR(?predicate), "sdg") || CONTAINS(STR(
        ?predicate), "skos"))
    )
}
"""

SDG_SERIES_RELATION_QUERY = """
SELECT ?subject ?predicate ?object ?label
WHERE{
    { ?subject ?predicate ?object }. 
    ?subject skos:prefLabel ?label. 
    FILTER (LANG(?label) = 'en' && ?predicate NOT IN (skos:inScheme) && 
        isIRI(?object) && (CONTAINS(STR(?predicate), "sdg") || 
        CONTAINS(STR(?predicate), "skos"))
    )
}
"""


def process_ecv(converter: curies.Converter):
    prefix = "ecv"
    has_ecv_product_requirement = TypeDef(
        reference=Reference(
            prefix=prefix, identifier="hasECVProductRequirement"
        ),
    )

    has_ecv_steward = TypeDef(
        reference=Reference(prefix=prefix, identifier="hasECVSteward"),
    )

    has_ecv_product = TypeDef(
        reference=Reference(prefix=prefix, identifier="hasECVProduct"),
    )

    has_scientific_area = TypeDef(
        reference=Reference(prefix=prefix, identifier="hasScientificArea")
    )

    has_data_source = TypeDef(
        reference=Reference(prefix=prefix, identifier='"hasDataSource"')
    )

    has_domain = TypeDef(
        reference=Reference(prefix=prefix, identifier='"hasDomain"')
    )

    curie_to_typedef = {
        prefix + ":hasECVSteward": has_ecv_steward,
        prefix + ":hasECVProduct": has_ecv_product,
        prefix + ":hasECVProductRequirement": has_ecv_product_requirement,
        prefix + ":hasScientificArea": has_scientific_area,
        prefix + ":hasDataSource": has_data_source,
        prefix + ":hasECVProducRequirement": has_ecv_product_requirement,
        prefix + ":hasDomain": has_domain,
    }

    graph = MODULE.ensure_rdf(
        url=ECV_KB_URL, parse_kwargs=dict(format="turtle")
    )
    curie_to_term = {}
    for res in graph.query(ECV_INFO_QUERY):
        curie = converter.compress(res["individual"], strict=True)
        # label is type Literal
        curie_to_term[curie] = Term(
            reference=Reference.from_curie(curie, res["label"], strict=True),
            definition=res["description"],
        )

    for res in graph.query(ECV_RELATION_QUERY):
        subject_curie = converter.compress(res["subject"])
        predicate_curie = converter.compress(res["predicate"])
        object_curie = converter.compress(res["object"])

        curie_to_term[subject_curie].append_relationship(
            curie_to_typedef[predicate_curie],
            Reference.from_curie(object_curie),
        )

    return curie_to_term


def process_eo(converter: curies.Converter):
    prefix = "eotaxonomy"
    graph = MODULE.ensure_rdf(url=EO_KB_URL, parse_kwargs=dict(format="turtle"))
    curie_to_term = {}
    for res in graph.query(EO_INFO_QUERY):
        curie = converter.compress(res["individual"], strict=True)
        curie_to_term[curie] = Term(
            reference=Reference.from_curie(curie, res["label"], strict=True),
            definition=res["description"],
        )

    has_sector = TypeDef(
        reference=Reference(prefix=prefix, identifier="hasSector")
    )
    has_user_group = TypeDef(
        reference=Reference(prefix=prefix, identifier="hasUserGroup")
    )
    from_domain = TypeDef(
        reference=Reference(prefix=prefix, identifier="fromDomain")
    )
    has_area = TypeDef(reference=Reference(prefix=prefix, identifier="hasArea"))
    from_market = TypeDef(
        reference=Reference(prefix=prefix, identifier="fromMarket")
    )
    has_domain = TypeDef(
        reference=Reference(prefix=prefix, identifier="hasDomain")
    )
    has_aligned_copernicus_service = TypeDef(
        reference=Reference(
            prefix=prefix, identifier="hasAlignedCopernicusService"
        )
    )
    curie_to_typedef = {
        prefix + ":hasSector": has_sector,
        prefix + ":hasUserGroup": has_user_group,
        prefix + ":fromDomain": from_domain,
        prefix + ":hasArea": has_area,
        prefix + ":fromMarket": from_market,
        prefix + ":hasDomain": has_domain,
        prefix + ":hasAlignedCopernicusService": has_aligned_copernicus_service,
    }
    for res in graph.query(EO_RELATION_QUERY):
        subject_curie = converter.compress(res["subject"])
        predicate_curie = converter.compress(res["predicate"])
        object_curie = converter.compress(res["object"])

        curie_to_term[subject_curie].append_relationship(
            curie_to_typedef[predicate_curie],
            Reference.from_curie(object_curie),
        )

    return curie_to_term


def process_sdg_goals(converter: curies.Converter):
    graph = MODULE.ensure_rdf(
        url=SDG_GOAL_URL, parse_kwargs=dict(format="turtle")
    )
    curie_to_term = {}

    for res in graph.query(SDG_INFO_QUERY):
        curie = converter.compress(res["individual"], strict=True)
        # sgd don't pass in description when creating references
        curie_to_term[curie] = Term(
            reference=Reference.from_curie(curie, res["label"], strict=True)
        )

    # FIXME add names to all typedefs!
    has_indicator = TypeDef(
        reference=Reference(prefix="sdgo", identifier="hasIndicator")
    )
    has_target = TypeDef(
        reference=Reference(prefix="sdgo", identifier="hasTarget")
    )
    is_indicator_of = TypeDef(
        reference=Reference(prefix="sdgo", identifier="isIndicatorOf")
    )
    is_target_of = TypeDef(
        reference=Reference(prefix="sdgo", identifier="isTargetOf")
    )
    broader = TypeDef(reference=Reference(prefix="skos", identifier="broader"))
    narrower = TypeDef(
        reference=Reference(prefix="skos", identifier="narrower")
    )
    curie_to_typedef = {
        "sdgo:hasIndicator": has_indicator,
        "sdgo:hasTarget": has_target,
        "sdgo:isIndicatorOf": is_indicator_of,
        "sdgo:isTargetOf": is_target_of,
        "skos:broader": broader,
        "skos:narrower": narrower,
    }
    for res in graph.query(SDG_GOALS_RELATION_QUERY):
        subject_curie = converter.compress(res["subject"])
        predicate_curie = converter.compress(res["predicate"])
        object_curie = converter.compress(res["object"])

        curie_to_term[subject_curie].append_relationship(
            curie_to_typedef[predicate_curie],
            Reference.from_curie(object_curie),
        )
    return curie_to_term


def process_sdg_series(converter: curies.Converter):
    graph = MODULE.ensure_rdf(
        url=SDG_SERIES_URL, parse_kwargs=dict(format="turtle")
    )
    curie_to_term = {}
    for res in graph.query(SDG_INFO_QUERY):
        curie = converter.compress(res["individual"], strict=True)
        curie_to_term[curie] = Term(
            reference=Reference.from_curie(curie, res["label"], strict=True)
        )

    broader = TypeDef(reference=Reference(prefix="skos", identifier="broader"))
    is_series_of = TypeDef(
        reference=Reference(prefix="sdgo", identifier="isSeriesOf")
    )
    curie_to_typedef = {
        "skos:broader": broader,
        "sdgo:isSeriesOf": is_series_of,
    }
    for res in graph.query(SDG_SERIES_RELATION_QUERY):
        subject_curie = converter.compress(res["subject"])
        predicate_curie = converter.compress(res["predicate"])
        object_curie = converter.compress(res["object"])

        curie_to_term[subject_curie].append_relationship(
            curie_to_typedef[predicate_curie],
            Reference.from_curie(object_curie),
        )

    return curie_to_term


def get_eiffel_ontology_terms() -> list[Term]:
    converter = Converter.from_prefix_map(
        {
            "ecv": "http://purl.org/eiffo/ecv#",
            "eotaxonomy": "http://purl.org/eiffo/eotaxonomy#",
            "sdg": "http://metadata.un.org/sdg/",
            "sdgo": "http://metadata.un.org/sdg/ontology#",
            "skos": "http://www.w3.org/2004/02/skos/core#",
        }
    )
    bioregistry.manager.synonyms["ecv"] = "ecv"
    bioregistry.manager.registry["ecv"] = bioregistry.Resource(
        name="EIFFEL Ontology",
        prefix="ecv",
        homepage="https://github.com/benmomo/eiffel-ontology/tree/main/ontology",
        description="An ontology for climate systems using Environment "
        "Climate Variables",
    )
    bioregistry.manager.synonyms["eotaxonomy"] = "eotaxonomy"
    bioregistry.manager.registry["eotaxonomy"] = bioregistry.Resource(
        name="EIFFEL Ontology",
        prefix="eotaxonomy",
        homepage="https://github.com/benmomo/eiffel-ontology/tree/main/ontology",
        description="An ontology for climate systems EO Taxonomy",
    )
    bioregistry.manager.synonyms["sdg"] = "sdg"
    bioregistry.manager.registry["sdg"] = bioregistry.Resource(
        name="EIFFEL Ontology",
        prefix="sdg",
        homepage="https://github.com/benmomo/eiffel-ontology/tree/main/ontology",
        description="An ontology for climate systems that define sustainable "
        "goals and development targets by the United Nations",
    )
    bioregistry.manager.synonyms["sdgo"] = "sdgo"
    bioregistry.manager.registry["sdgo"] = bioregistry.Resource(
        name="EIFFEL Ontology",
        prefix="sdgo",
        homepage="https://github.com/benmomo/eiffel-ontology/tree/main/ontology",
        description="An ontology for climate systems that define sustainable "
        "goals and development targets by the United Nations",
    )
    bioregistry.manager.synonyms["skos"] = "skos"
    bioregistry.manager.registry["skos"] = bioregistry.Resource(
        name="EIFFEL Ontology",
        prefix="skos",
        homepage="https://github.com/benmomo/eiffel-ontology/tree/main/ontology",
        description="An ontology for climate systems that define sustainable "
        "goals and development targets by the United Nations",
    )

    rv = []

    rv.extend(process_ecv(converter).values())
    rv.extend(process_eo(converter).values())
    rv.extend(process_sdg_goals(converter).values())
    rv.extend(process_sdg_series(converter).values())

    return rv


if __name__ == "__main__":
    term_list = get_eiffel_ontology_terms()
