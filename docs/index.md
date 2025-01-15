---
layout: home
---

# Interacting with MIRA template models using Python code

## Accessing model attributes

### Observables

### Initials

### Templates

## Template Model operations

### Adding a parameter

Users can use the `add_parameter` method which is a template model instance method that adds a parameter
to the template model. The only required parameter is the id the parameter. 

```python
from mira.examples.sir import sir

sir.add_parameter("mu")
```

#### Documentation
- `add_parameter(parameter_id, name, description, value, distribution, units_mathml)`
  - `parameter_id`: `str`
    - The id of the parameter
  - `name`: `Optional[str]`
    - An alternative name for the parameter
  - `description`: `Optional[str]`
    - The description of the parameter
  - `value`: `Optional[float]`
    - The value of the parameter
  - `distribution`: `Optional[Dict[str, Any]]`
    - The distribution of the parameter
  - `units_mathml`: `Optional[str]`
    - The units of the parameter in mathml form

#### Common use-cases
- If we wanted to add pet specific compartments to a human-centric SIR epidemiology model, we can use add pet specific
parameters with values for simulation purposes.

```python
from mira.examples.sir import sir

sir.add_parameter("mu_pet", value=0.0003)
```
### Composition

The composition method takes in a list of template models and composes them into
a single
template model. The list must contain at least two template models.

```python
from mira.examples.sir import sir, sir_2_city
from mira.metamodel.composition import compose

tm_list = [sir, sir_2_city]
composed_tm = compose(tm_list)
```

- `tm_list`: `List[TemplateModel]`
    - A list of template models to be composed

The composition functionality prioritizes template model attributes (parameters,
initials, templates, annotation, time, model time, etc.)
of the first template model in the list.

#### Common use-cases

- If we had five different template representing variations of the base SIR
  epidemiological model, we can combine them using model composition.

```python
from mira.metamodel import *

susceptible = Concept(name="susceptible_population",
                      identifiers={"ido": "0000514"})
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

In this section we will discuss the behavior of how concepts are composed
different circumstances.

- If two concepts have the same name and identifiers
    - If two concepts from different template models being composed having
      matching
      names and identifiers, then they will be composed into one concept.
- If two concepts have the same name but mismatched identifiers
    - They will be treated as separate concepts
- If two concepts don't have the same name but matching identifiers
    - They will be composed into the same concept, with the name of the first
      concept taking priority.
- If two concepts have matching names and one has identifiers and the other
  doesn't
    - The concepts are composed into the same concept while preserving the
      identifiers
- The concepts have matching names and neither has identifiers
    - The concepts are composed into the same concept

Here are examples highlighting the different cases in which concepts can be
composed.

```python
from mira.metamodel import *

S1 = Concept(name="Susceptible", identifiers={"ido": "0000514"})
I1 = Concept(name="Infected", identifiers={"ido": "0000511"})
R1 = Concept(name="Recovery", identifiers={"ido": "0000592"})

S2 = Concept(name="Susceptible", identifiers={"ido": "0000513"})
I2 = Concept(name="Infected", identifiers={"ido": "0000512"})
R2 = Concept(name="Recovery", identifiers={"ido": "0000593"})

S3 = Concept(name="S", identifiers={"ido": "0000514"})
I3 = Concept(name="I", identifiers={"ido": "0000511"})
R3 = Concept(name="R", identifiers={"ido": "0000592"})

S4 = Concept(name="S")
I4 = Concept(name="I")
R4 = Concept(name="R")

model_A1 = TemplateModel(
    templates=[
        ControlledConversion(
            name='Infection',
            subject=S1,
            outcome=I1,
            controller=I1
        )
    ],
    parameters={
        'b': Parameter(name='b', value=1.0)
    }
)

model_B1 = TemplateModel(
    templates=[
        NaturalConversion(
            name='Recovery',
            subject=I1,
            outcome=R1
        )
    ],
    parameters={
        'g': Parameter(name='g', value=1.0)
    }
)

model_B2 = TemplateModel(
    templates=[
        NaturalConversion(
            name='Recovery',
            subject=I2,
            outcome=R2
        )
    ],
    parameters={
        'g': Parameter(name='g', value=1.0)
    }
)

model_B3 = TemplateModel(
    templates=[
        NaturalConversion(
            name='Recovery',
            subject=I3,
            outcome=R3
        )
    ],
    parameters={
        'g': Parameter(name='g', value=1.0)
    }
)

model_B4 = TemplateModel(
    templates=[
        NaturalConversion(
            name='Recovery',
            subject=I4,
            outcome=R4
        )
    ],
    parameters={
        'g': Parameter(name='g', value=1.0)
    }
)

model_A3 = TemplateModel(
    templates=[
        ControlledConversion(
            name='Infection',
            subject=S3,
            outcome=I3,
            controller=I3
        )
    ],
    parameters={
        'b': Parameter(name='b', value=1.0)
    }
)

model_A4 = TemplateModel(
    templates=[
        ControlledConversion(
            name='Infection',
            subject=S4,
            outcome=I4,
            controller=I4
        )
    ],
    parameters={
        'b': Parameter(name='b', value=1.0)
    }
)

# (matching name and ids) 
# composed into a single concept
model_AB11 = compose([model_A1, model_B1])

# matching names, mismatched ids
# not composed into a single concept
model_AB12 = compose([model_A1, model_B2])

# mismatched names, matching ids
# composed into a single concept
model_AB13 = compose([model_A1, model_B3])

# matching names, no id + yes id
# composed into a single concept
model_AB34 = compose([model_A3, model_B4])

# matching names, no id + no id
# composed into a single concept
model_AB44 = compose([model_A4, model_B4])
```

### Stratification

The stratification method can take in an exhaustive list of arguments and
multiplies a template model into several strata.

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
    - `params_to_stratify`: `Optional[Collection[str]]`
        - The list of parameter names that will be stratified
    - `concepts_to_stratify`: `Optional[Collection[str]]`
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
    - `modify_name`: `Optional[bool]`
        - Setting this to true will rename concept names to include strata names
    - `param_renaming_uses_strata_names`: `Optional[bool]`
        - Setting this to true will rename parameter names to include strata
          names

If we wanted to rename the S and I compartments and accompanying parameters from
a SIR epidemiological model to include
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
    - `structure`: `Optional[Iterable[Tuple[str, str]]]`
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

An example where we would want to specify structure but not assume complete
network structure is if we
were to stratify a model based on vaccination status. This is because people can
transition from being unvaccinated
to vaccinated; however, it's impossible once someone is vaccinated to transition
to unvaccinated.

We would pass in an iterable that contains a single tuple pair
`("unvaccinated", "vaccinated")` that represents
people getting vaccinated in a SIR epidemiological model.

```python
from mira.examples.sir import sir as model
from mira.metamodel.ops import stratify

key = "vaccination_status"
strata = ["unvaccinated", "vaccinated"]
stratify(model, key, strata, structure=[("unvaccinated", "vaccinated")])
```

##### Split control based relationships on stratification

- Setting the `cartesian_control` argument to true will split all control based
  relationships based on the stratification.
    - `cartesian_control`: `Optional[bool]`
        - Setting this to true splits all control relationships in the model

The argument should be set to true for a SIR epidemiology model stratified on
age. As the transition from the susceptible
to the infected compartment for a certain age group is controlled by the
infected compartment of other age groups.

```python
from mira.examples.sir import sir as model
from mira.metamodel.ops import stratify

key = "age"
strata = ["under50", "50+"]
stratify(model, key, strata, cartesian_control=True)
```

We would set `cartesian_control` to false for a SIR epidemiology model based on
age, since the infected population in one city will not
affect the infection of the susceptible population in another city.

```python
from mira.examples.sir import sir as model
from mira.metamodel.ops import stratify

key = "city"
strata = ["Boston", "Miami"]
stratify(model, key, strata, cartesian_control=False)
```