---
layout: home
---
# Interacting with MIRA template models using Python code

## Accessing model attributes

### Observables

### Initials

### Templates

## Model operations

### Composition

The composition method takes in a list of template models and composes them into a single
template model. The list must contain at least two template models. 

```python
from mira.examples.sir import sir, sir_2_city
from mira.metamodel.composition import compose

tm_list = [sir,sir_2_city]
composed_tm = compose(tm_list)
```

- `tm_list`: `Collection[TemplateModel]`
  -  A list of template models to be composed

The composition functionality prioritizes template model attributes (parameters, initials, templates, annotation, time, model time, etc.)
of the first template model in the list.

#### Common use-cases
-  If we had five different template representing variatians of the base SIR epimidelogical model, we can combine them using model composition.

```python
from mira.metamodel import *

susceptible = Concept(name="susceptible_population", identifiers={"ido": "0000514"})
hospitalized = Concept(name="hospitalized", identifiers={"ncit": "C25179"})
infected = Concept(name="infected_population", identifiers={"ido": "0000511"})
recovered = Concept(name="immune_population", identifiers={"ido": "0000592"})
dead = Concept(name="dead", identifiers={"ncit": "C28554"})
quarantined = Concept(name="quarantined", identifiers={})

infection = ControlledConversion(
    subject=susceptible,
    outcome=infected,
    controller=infected,
)
recovery = NaturalConversion(
    subject=infected,
    outcome=recovered,
)

reinfection = ControlledConversion(
    subject=recovered,
    outcome=infected,
    controller=infected,
)

to_quarantine = NaturalConversion(
    subject=susceptible, 
    outcome=quarantined
)

from_quarantine = NaturalConversion(
    subject=quarantined, 
    outcome=susceptible
)

dying = NaturalConversion(
    subject=infected, 
    outcome=dead
)

hospitalization = NaturalConversion(
    subject=infected, 
    outcome=hospitalized
)

hospitalization_to_recovery = NaturalConversion(
    subject=hospitalized, 
    outcome=recovered
)

hospitalization_to_death = NaturalConversion(
    subject=hospitalized, 
    outcome=dead
)

sir = TemplateModel(
    templates=[
        infection,
        recovery,
    ]
)

sir_reinfection = TemplateModel(
    templates=[
        infection, 
        recovery, 
        reinfection
    ]
)

sir_quarantined = TemplateModel(
    templates=[
        infection, 
        to_quarantine, 
        from_quarantine, 
        recovery
    ]
)

sir_dying = TemplateModel(
    templates=[
        infection,
        dying,
        recovery,
    ]
)

sir_hospitalized = TemplateModel(
    templates=[
        infection,
        hospitalization,
        hospitalization_to_recovery,
        hospitalization_to_death,
    ]
)

model_list = [
    sir_reinfection,
    sir_quarantined,
    sir_dying,
    sir_hospitalized,
    sir,
]

composed_model = compose(tm_list=model_list)
```

#### Examples of concept composition
- In this section we will discuss the behavior of how concepts are composed under different circumstances. 

##### If two concepts have the same name and identifier
- If two concepts from different template models being composed having matching names and identifiers, then they will be composed into one concept.

Here are examples highlighting the different cases in which concepts can be composed. 
```python
# stub code 
```

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
    - If an argument isn't supplied, then all concepts and/or parameters will be
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
  set the values of the `modify_names` and `param_renaming_uses_strata_names`
  flags.
    - `modify_name`: `bool`
        - Setting this to true will rename concept names to include strata names
    -  `param_renaming_uses_strata_names`: `bool`
        - Setting this to true will rename parameter names to include strata
          names

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