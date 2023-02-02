# This script builds custom subsets of large ontologies for import into the MIRA DKG

# See documentation for installing robot at http://robot.obolibrary.org/
# and for ``robot extract`` on http://robot.obolibrary.org/extract.html
# note that STAR just picks terms and MIREOT allows for subtree selection

robot extract --method STAR --copy-ontology-annotations=true \
    --input-iri https://github.com/EBISPOT/covoc/releases/download/current/covoc.owl \
    --term-file covoc_terms.txt \
    --output-iri https://raw.githubusercontent.com/indralab/mira/main/mira/dkg/resources/covoc_slim.json \
    --output covoc_slim.json

robot extract --method STAR --copy-ontology-annotations=true \
    --input-iri http://www.ebi.ac.uk/efo/efo.owl \
    --term-file efo_terms.txt \
    --output-iri https://raw.githubusercontent.com/indralab/mira/main/mira/dkg/resources/efo_slim.json \
    --output efo_slim.json

robot extract --method MIREOT --copy-ontology-annotations=true \
    --input-iri http://purl.obolibrary.org/obo/ncit.owl \
    --output ncit_slim.json \
    --output-iri https://raw.githubusercontent.com/indralab/mira/main/mira/dkg/resources/ncit_slim.json \
    --branch-from-term "obo:NCIT_C17005" \
    --branch-from-term "obo:NCIT_C25636" \
    --branch-from-term "obo:NCIT_C28320" \
    --branch-from-term "obo:NCIT_C171133" \
    --branch-from-term "obo:NCIT_C28554" \
    --branch-from-term "obo:NCIT_C25179" \
    --branch-from-term "obo:NCIT_C71902" \
    --branch-from-term "obo:NCIT_C154475" \
    --branch-from-term "obo:NCIT_C173636" \
    --branch-from-term "obo:NCIT_C20189" \
    --branch-from-term "obo:NCIT_C27992" \
    --branch-from-term "obo:NCIT_C27993" \
    --branch-from-term "obo:NCIT_C168447" \
    --branch-from-term "obo:NCIT_C18020" \
    --branch-from-term "obo:NCIT_C21541"

# There aren't nice ways to stick comments inside multi-line commands,
#  so here's some documentation on what these terms are:
# C20189 -> Property or Attribute
# C27993 -> General qualifier
# C27992 -> disease qualifier
# C18020 -> diagnostic procedure

# these ontologies can all be merged together with the following command,
# but this makes provenance a little funky in the DKG build
# robot merge --inputs "*_slim.owl" --output merged.owl
