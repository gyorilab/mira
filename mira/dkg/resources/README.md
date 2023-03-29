# MIRA Resources

If you want to add additional terms from NCIT to the DKG, take the following
steps:

1. Go into `custom_ontology.sh` and find the `robot extract` command corresponding to NCIT
2. You should see a list of `--branch-from-term` commands. make a new line with another one
   of these, switching in your desired NCIT term. Note that this will take the whole branch
   under your term, so be specific!
3. Run `custom_ontology.sh`. This requires having `robot` and `python` installed and available.

## `manual.obo`

Some of the ontology artifacts are just too big to work with ROBOT, so `manual.obo` is a place to dump any extra terms
from those
