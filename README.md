# MIRA

MIRA is a framework for representing systems using ontology-grounded **meta-model templates**, and generating various model implementations and exchange formats from these templates. It also implements algorithms for assembling and querying **domain knowledge graphs** in support of modeling.

Example notebooks
  - Defining multiple model variants using MIRA Templates: [notebook](https://github.com/indralab/mira/blob/main/notebooks/metamodel_intro.ipynb)
  - Generating an executable model from MIRA Templates and running simulation: [notebook](https://github.com/indralab/mira/blob/main/notebooks/simulation.ipynb)
  
MIRA builds on and generalizes prior work including
- [EMMAA](https://emmaa.indra.bio): A framework for automatically maintaining a set of models surrounding the biology of viral pandemics, cancer, and other disease areas based on new findings as soon as they appear in the literature. Models are automatically analyzed against observations.
- [INDRA](https://indra.bio): An automated model building system from literature mining, structured databases, and natural language input for molecular biology. INDRA Statements serve as domain-specific instances of MIRA Templates.
- [INDRA CoGEx](https://discovery.indra.bio): A 3*10^7-relation scale domain-specific knowledge graph of biomedicine combining causal mechanisms with ontologies and relations derived from data.
- [INDRA World](https://github.com/indralab/indra_world): A generalization of INDRA to modeling socio-economic systems, using a templated approach representing causal influence, events, and concepts.

## Documentation

The documentation can be built locally with `tox -e docs` and can be browsed
starting with `docs/build/index.html`.
