# MIRA

[![Documentation Status](https://readthedocs.org/projects/miramodel/badge/?version=latest)](https://miramodel.readthedocs.io/en/latest/?badge=latest)

MIRA is a framework for representing systems using ontology-grounded **meta-model templates**, and generating various model implementations and exchange formats from these templates. It also implements algorithms for assembling and querying **domain knowledge graphs** in support of modeling.

## Example notebooks

* Defining multiple model variants using MIRA Templates: [Notebook](https://github.com/indralab/mira/blob/main/notebooks/metamodel_intro.ipynb)
* Generating an executable model from MIRA Templates and running simulation: [Notebook](https://github.com/indralab/mira/blob/main/notebooks/simulation.ipynb)

## Related work

MIRA builds on and generalizes prior work including:

* [EMMAA](https://emmaa.indra.bio): A framework for automatically maintaining a set of models surrounding the biology of viral pandemics, cancer, and other disease areas based on new findings as soon as they appear in the literature. Models are automatically analyzed against observations.
* [INDRA](https://indra.bio): An automated model building system from literature mining, structured databases, and natural language input for molecular biology. INDRA Statements serve as domain-specific instances of MIRA Templates.
* [INDRA CoGEx](https://discovery.indra.bio): A 3*10^7-relation scale domain-specific knowledge graph of biomedicine combining causal mechanisms with ontologies and relations derived from data.
* [INDRA World](https://github.com/indralab/indra_world): A generalization of INDRA to modeling socio-economic systems, using a templated approach representing causal influence, events, and concepts.

## Installation

The most recent code and data can be installed directly from GitHub with:

```python
python -m pip install git+https://github.com/indralab/mira.git
```

To install in development mode, use the following:

```python
git clone git+https://github.com/indralab/mira.git
cd mira
python -m pip install -e .
```

## Documentation

Full documentation can be found on [here](https://miramodel.readthedocs.io).
