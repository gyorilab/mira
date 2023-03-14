# Model-level Metadata Annotation

This document describes the metadata that we would like to see TA-1 extracting from papers, code, and other artifacts that describe the model, in addition to the core dynamics.

In https://github.com/indralab/mira/pull/138, we implemented this data model so MIRA can extract these fields from SBML files in the BioModels database and more generally represent these data in a structured way.

## Schema with Examples

Field | Field Description | Example (From Bertozzi 2020 SIR model)
-- | -- | --
Name | Human-readable label | SIR model of scenarios of COVID-19 spread in CA and NY
Description | Description of the model | We detail three regional scale models for forecasting and assessing the course of the pandemic ...
License | A string representing the model string, ideally from SPDX | CC0
Authors | A list of authors | Andrea L Bertozzi, Elisa Franco, George Mohler, Martin B Short, Daniel Sledge
References | A list of references given as CURIEs, ideally using PubMed, DOI, or PMC | pubmed:32616574
Time Start | The date and time of the beginning of the applicability of the model | March, 2020
Time End | The date and time of the end of the applicability of the model | August, 2020
Location(s) | The location(s) of applicability of the model given as CURIEs, ideally using GeoNames or Wikidata | geonames:5128581, geonames:5332921
Pathogen(s) | A list of pathogens present in the model given as CURIEs, ideally using NCBITaxon | ncbitaxon:2697049
Host(s) | A list of hosts present in the model given as CURIEs, ideally using NCBITaxon | ncbitaxon:9606
Model Type(s) | A list of model type annotations with the Mathematical Modeling Ontology (MAMO) vocabulary | mamo:0000028, mamo:0000046
Coordinate System | The coordinate system used in the model (e.g., spherical, cylindrical) |  


## Example as JSON

The following is a concrete example of data in the JSON format from the [Bertozzi 2020 SIR model](https://www.pnas.org/doi/10.1073/pnas.2006520117) (see also [biomodels.db:BIOMD0000000956](https://www.ebi.ac.uk/biomodels/BIOMD0000000956) for a structured SBML version of this data.

The JSON schema for this data is encoded in https://github.com/indralab/mira/blob/improve-sbml-annotation-processing/mira/metamodel/schema.json.

```json
{
  "name": "SIR model of scenarios of COVID-19 spread in CA and NY",
  "description": "The coronavirus disease 2019 (COVID-19) pandemic has ..",
  "license": "CC0",
  "authors": [
    {"name": "Andrea L Bertozzi"},
    {"name": "Elisa Franco"},
    {"name": "George Mohler"},
    {"name": "Martin B Short"},
    {"name": "Daniel Sledge"}
  ],
  "references": ["pubmed:32616574"],
  "time_start": "2020-03-01T00:00:00",
  "time_end": "2020-08-01T00:00:00",
  "locations": ["geonames:5128581", "geonames:5332921"],
  "pathogens": ["ncbitaxon:2697049"],
  "diseases": ["doid:0080600"],
  "hosts": ["ncbitaxon:9606"],
  "model_types": ["mamo:0000028", "mamo:0000046"]
}
```
