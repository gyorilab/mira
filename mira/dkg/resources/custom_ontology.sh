# This script builds custom subsets of large ontologies for import into the MIRA DKG

# See documentation for installing robot at http://robot.obolibrary.org/
# and for ``robot extract`` on http://robot.obolibrary.org/extract.html
# note that STAR just picks terms and MIREOT allows for subtree selection

robot extract --method STAR --copy-ontology-annotations=true \
    --input-iri https://github.com/EBISPOT/covoc/releases/download/current/covoc.owl \
    --term-file covoc_terms.txt \
    --output covoc_slim.json

robot extract --method STAR --copy-ontology-annotations=true \
    --input-iri http://www.ebi.ac.uk/efo/efo.owl \
    --term-file efo_terms.txt \
    --output efo_slim.json

robot extract --method MIREOT --copy-ontology-annotations=true \
    --input-iri http://purl.obolibrary.org/obo/ncit.owl \
    --output ncit_slim.json \
    --branch-from-term "obo:NCIT_C17005" \
    --branch-from-term "obo:NCIT_C25636" \
    --branch-from-term "obo:NCIT_C28320" \
    --branch-from-term "obo:NCIT_C171133" \
    --branch-from-term "obo:NCIT_C28554" \
    --branch-from-term "obo:NCIT_C25179" \
    --branch-from-term "obo:NCIT_C71902" \
    --branch-from-term "obo:NCIT_C154475" \
    --branch-from-term "obo:NCIT_C21541"

# these ontologies can all be merged together with the following command,
# but this makes provenance a little funky in the DKG build
# robot merge --inputs "*_slim.owl" --output merged.owl
