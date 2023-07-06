"""Constants for the DKG Build."""

#: The used for the nodes files in the neo4j bulk import
NODE_HEADER = (
    "id:ID",
    ":LABEL",
    "name:string",
    "synonyms:string[]",
    "obsolete:boolean",
    "type:string",
    "description:string",
    "xrefs:string[]",
    "alts:string[]",
    "version:string",
    "property_predicates:string[]",
    "property_values:string[]",
    "xref_types:string[]",
    "synonym_types:string[]",
    "source:string",
)

#: The used for the edges files in the neo4j bulk import
EDGE_HEADER = (
    ":START_ID",
    ":END_ID",
    ":TYPE",
    "pred:string",
    "source:string",
    "graph:string",
    "version:string",
)
