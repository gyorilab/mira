---
layout: home
---

Welcome to the MIRA static site.

- [ontology](/ontology)

# Interacting with MIRA template models using Python code

## Accessing model attributes

### Observables

### Initials

### Templates

## Model operations

### Composition

### Stratification

The stratification method can take in an exhaustive list of arguments and
multiplies a template model into several strata.

#### Required arguments

The three required arguments are the input template model, key, and strata

```python
from mira.examples.sir import sir as model
from mira.metamodel.ops import stratify

key = "vaccination_status"
strata = ["unvaccinated", "vaccinated"]
model = stratify(model, key, strata)
```

- `model`: `TemplateModel`
    - The input template model to be stratified
- `key`:`str`
    - The singular name of the stratification
- `strata`: `Collections[str]`
    - The list of values used for stratification

#### Common use-cases

##### Concept and parameter stratification

- If you want to not stratify certain parameters or concepts in the template
  model, you can pass in an optional collection of parameter and concept names
  to the
  method under arguments `params_to_stratify` and `concepts_to_stratify`.
    - `params_to_stratify`: `Collection[str]`
        - The list of parameter names that will be stratified
    - `concepts_to_stratify`: `Collection[str]`
        - The list of concept names that will be stratified
    - If an argument isn't supplied, then all concept and/or parameters will be
      stratified

If you wanted to stratify the susceptible and exposed compartments along with
certain parameters in a SIR epidemiological model based on vaccination status.

```python
from mira.examples.sir import sir as model
from mira.metamodel.ops import stratify

key = "vaccination_status"
strata = ["unvaccinated", "vaccinated"]
stratify(model, key, strata, concepts_to_stratify=["S", "I"],
         params_to_stratify=["c", "beta", "m"])
```

##### Concept and parameter renaming

- By default, the stratify operator will rename stratified concepts to include
  the name of the strata and not rename parameters to include the strata names.
  We can
  set the values of the `param_renaming_uses_strata_names` and `modify_names`
  flags.
    - `param_renaming_uses_strata_names`: `bool`
        - Setting this to true will rename parameter names to include strata
          names
    - `modify_name`: `bool`
        - Setting this to true will rename concept names to include strata names

If we wanted to rename the S and I compartments and accompanying parameters from a SIR epidemiological model to include
strata names.

```python
from mira.examples.sir import sir as model
from mira.metamodel.ops import stratify

key = "vaccination_status"
strata = ["unvaccinated", "vaccinated"]
stratify(model, key, strata, concepts_to_stratify=["S", "I"],
         params_to_stratify=["c", "beta", "m"],
         param_renaming_uses_strata_names=True,
         modify_names=True)
```

##### Enforcing a directed network structure

- If you wanted to specify certain pairs of compartments to have a directed
  network structure where
  each of the compartments in the pair will be appropriately stratified
  according to the strata, then
  an optional iterable of tuple pairs containing compartment names can be passed
  to the `structure`
  argument.
    - `structure`: `Iterable[Tuple[str, str]]`
        - The list of tuple pairs that denote a directed edge from the first
          compartment in each tuple
          to the second compartment in the same tuple
            - If no argument is supplied, the stratify method will assume a
              complete network structure
            - If no structure is necessary, then pass in an empty list

An example where we wouldn't want any structure is if we were to stratify the
model by age. This is
because for the purpose of modeling, people do not age.

Here we stratify the compartments in an SIR epidemiological model by age groups.
We pass in an empty list to the `structure` argument.

```python
from mira.examples.sir import sir as model
from mira.metamodel.ops import stratify

key = "age"
strata = ["under50", "50+"]
stratify(model, key, strata, structure=[])
```
      
An example where we would want to specify structure but not assume complete network structure is if we
were to stratify a model based on vaccination status. This is because people can transition from being unvaccinated
to vaccinated; however, it's impossible once someone is vaccinated to transition to unvaccinated. 

We would pass in an iterable that contains a single tuple pair `("unvaccinated", "vaccinated")` that represents
people getting vaccinated in a SIR epidemiological model. 

```python
from mira.examples.sir import sir as model
from mira.metamodel.ops import stratify

key = "vaccination_status"
strata = ["unvaccinated", "vaccinated"]
stratify(model, key, strata, structure=[("unvaccinated","vaccinated")])
```

##### Split control based relationships on stratification
- Setting the `cartesian_control` argument to true will split all control based relationships based on the stratification.
  - `cartesian_control`: `bool`
    - Setting this to true splits all control relationships in the model 

The argument should be set to true for a SIR epidemiology model stratified on age. As the transition from the susceptible
to the infected compartment for a certain age group is controlled by the infected compartment of other age groups. 

```python
from mira.examples.sir import sir as model
from mira.metamodel.ops import stratify
key = "age"
strata = ["under50", "50+"]
stratify(model, key, strata, cartesian_control=True)
```

We would set `cartesian_control` to false for a SIR epidemiology model based on age, since the infected population in one city will not
affect the infection of the susceptible population in another city. 

```python
from mira.examples.sir import sir as model
from mira.metamodel.ops import stratify
key = "city"
strata = ["Boston", "Miami"]
stratify(model, key, strata, cartesian_control=False)
```