# This script builds custom subsets of large ontologies for import into the MIRA DKG

# See documentation for installing robot at http://robot.obolibrary.org/
# and for ``robot extract`` on http://robot.obolibrary.org/extract.html

robot extract --method TOP \
    -I https://github.com/EBISPOT/covoc/releases/download/current/covoc.owl \
    --term-file covoc_terms.txt \
    --output covoc_slim.owl

robot extract --method TOP \
    -I http://www.ebi.ac.uk/efo/efo.owl \
    --term-file efo_terms.txt \
    --output efo_slim.owl

robot extract \
    -I http://purl.obolibrary.org/obo/ncit.owl \
    --method MIREOT \
    --output ncit_slim.owl \
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
