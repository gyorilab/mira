# MIRA

[![Documentation Status](https://readthedocs.org/projects/miramodel/badge/?version=latest)](https://miramodel.readthedocs.io/en/latest/?badge=latest)

<img src="https://raw.githubusercontent.com/gyorilab/mira/main/docs/mira_logo.png" height="300" />

MIRA is a framework for representing systems using ontology-grounded **meta-model templates**, and generating various model implementations and exchange formats from these templates. It also implements algorithms for assembling and querying **domain knowledge graphs** in support of modeling.

## Resources

* Template JSON schema: [schema.json](https://github.com/gyorilab/mira/blob/main/mira/metamodel/schema.json)
* Epidemiology Domain Knowledge Graph (DKG) service: [DKG service](http://34.230.33.149:8771/)
* MIRA Metaregistry service: [Metaregistry service](http://34.230.33.149:8772/) 

## Example notebooks

* Defining multiple model variants using MIRA Templates: [Notebook 1](https://github.com/gyorilab/mira/blob/main/notebooks/metamodel_intro.ipynb)
* Generating an executable model from MIRA Templates and running simulation: [Notebook 2](https://github.com/gyorilab/mira/blob/main/notebooks/simulation.ipynb)
* Stratifying and visualizing MIRA models, and exporting as Petri nets: [Notebook 3](https://github.com/gyorilab/mira/blob/main/notebooks/viz_strat_petri.ipynb)
* Processing an SBML model from BioModels, visualizing and exporting into Petri nets: [Notebook 4](https://github.com/gyorilab/mira/blob/main/notebooks/biomodels.ipynb)
* Using the MIRA Domain Knowledge Graph REST API: [Notebook 5](https://github.com/gyorilab/mira/blob/main/notebooks/dkg_api.ipynb)
* Using the Model REST API to perform various model operations: [Notebook 6](https://github.com/gyorilab/mira/blob/main/notebooks/model_api.ipynb)
* Using the web client in python that connects to the REST API: [Notebook 7](https://github.com/gyorilab/mira/blob/main/notebooks/web_client.ipynb)
* Demonstrating MIRA TemplateModel capabilities [Notebook 8](https://github.com/gyorilab/mira/blob/main/notebooks/Hackathon%20Scenario%201.ipynb)
* Rapid construction of DKGs in ASKEM: [Notebook 9](https://github.com/gyorilab/mira/blob/main/notebooks/Rapid%20construction%20of%20new%20DKGs.ipynb)
* Implement a masking intervention in a compartmental model to simulate 
  epidemic trajectories under different scenarios: 
  [Notebook 10](https://github.com/gyorilab/mira/blob/main/notebooks/hackathon_2023.07/scenario1.ipynb)
* Benchmarking the efficacy of DKG groundings on a set of COVID EPI Models: 
  [Notebook 11](https://github.com/gyorilab/mira/blob/main/notebooks/hackathon_2023.10/Model%20Comparison.ipynb)
 

[//]: # (Gromet Export fixme: uncomment when gromet works again)

## Related work

MIRA builds on and generalizes prior work including:

* [EMMAA](https://emmaa.indra.bio): A framework for automatically maintaining a set of models surrounding the biology of viral pandemics, cancer, and other disease areas based on new findings as soon as they appear in the literature. Models are automatically analyzed against observations.
* [INDRA](https://indra.bio): An automated model building system from literature mining, structured databases, and natural language input for molecular biology. INDRA Statements serve as domain-specific instances of MIRA Templates.
* [INDRA CoGEx](https://discovery.indra.bio): A 3*10^7-relation scale domain-specific knowledge graph of biomedicine combining causal mechanisms with ontologies and relations derived from data.
* [INDRA World](https://github.com/gyorilab/indra_world): A generalization of INDRA to modeling socio-economic systems, using a templated approach representing causal influence, events, and concepts.

## Installation

The most recent code and data can be installed directly from GitHub with:

```shell
python -m pip install git+https://github.com/gyorilab/mira.git
```

To install in development mode, use the following:

```shell
git clone git+https://github.com/gyorilab/mira.git
cd mira
python -m pip install -e .
```

If you wanted to install extra dependencies that aren't listed under `install_requires`
such as the packages required for running ode simulations, use the following:
```shell
python -m pip install -e .[ode]
```

To install multiple dependency blocks listed in `setup.cfg`, run the following:
```shell
python -m pip install -e .[ode,docs]
```

### Extra dependency blocks/packages required for modules
  
  | Module                           | Dependency   |
  |----------------------------------|--------------|
  | `mira/modeling/ode.py`           | `ode`        |
  | `mira/modeling/viz.py`           | `viz`        |
  | `mira/sources/biomodels.py`      | `biomodels`  |
  | `mira/sources/sbml/processor.py` | `sbml`       |
  | `mira/sources/space_latex.py`    | `tests`      |


## Documentation

Full documentation can be found [here](https://miramodel.readthedocs.io).

## Funding

The development of MIRA is funded by the DARPA ASKEM program, grant number HR00112220036.
