---
layout: home
---

# Interacting with MIRA template models using Python code

## Accessing model attributes

### Observables

Observables associated with a template model can be accessed using the
`observables` attribute of a template model object.

- `observables`: `Dict[str,Observable]`
    - The dictionary of observables in a template model

#### Observable operations

- While we don't have any direct methods to add, remove, or modify observables,
  we can use the `observables` attribute to perform
  any observable specific operations.

##### Adding an observable

A user might want to add a new observable to keep track of a new combination
of compartment values

Users can define a key-value pair where the key represents the id of the
observable and the value is a newly created
observable object to add to the template model. We create a new observable
object with name and expression to keep track
of the total number of infected in a SIR epidemiology model.

If there already exists a key-value pair in the `observables` dictionary using
the same key, then the old observable object will
be overwritten by the new one.

```python
from mira.metamodel import *
from mira.examples.sir import sir

key = "total_infections"
expression = SympyExprStr("I")
total_infections_observable = Observable(name=key, expression=expression)

sir.observables[key] = total_infections_observable
```

Users can also add multiple observables at once using the Python dictionary
`update()` method. The `update` method is a dictionary instance method that can
take in another dictionary and combines both dictionaries. 

The passed-in dictionary takes priority and will overwrite the
key-value pairs of the original
dictionary if they share the same key.

```python
from mira.metamodel import *
from mira.examples.sir import sir

key_infections = "total_infections"
expression_infections = SympyExprStr("I")
total_infections_observable = Observable(name=key_infections,
                                         expression=expression_infections)

key_susceptible = "total_susceptible"
expression_susceptible = SympyExprStr("S")
total_susceptible_observable = Observable(name=key_susceptible,
                                          expression=expression_susceptible)

new_observables = {key_infections: total_infections_observable,
                   key_susceptible: total_susceptible_observable}

sir.observables.update(new_observables)
```

##### Removing an observable

A user might want to remove an observable because it's no longer needed.

We can utilize the dictionary `pop()` method that takes in a key and removes
the key-value pair from the dictionary if
it exists in the dictionary.

```python
from mira.metamodel import *
from mira.examples.sir import sir

key = "total_infections"
expression = SympyExprStr("I")
total_infections_observable = Observable(name=key, expression=expression)

sir.observables[key] = total_infections_observable

sir.observables.pop(key)
```

##### Modifying an observable

A user might want to modify the expression of an observable to keep track of a
different combination of compartments

We can use the Python dictionary method `get()` which takes in a key and returns a
reference to the observable object
that we'd like to modify if it exists in the `observables` dictionary.

```python
from mira.metamodel import *
from mira.examples.sir import sir

# Add the observable
key = "total_infections"
expression = SympyExprStr("I")
total_infections_observable = Observable(name=key, expression=expression)

sir.observables[key] = total_infections_observable

# stratify to add a species specific strata for the infected compartment
model = stratify(sir, "species", ["human", "pet"], concepts_to_stratify=["I"])

# keep track of both human and pet infections for the total number of infected
sir.observables.get(key).expression = SympyExprStr("I_human+I_pet")
```

### Initials

Like observables, we don't have any direct methods to add, remove, or modify initials,
but we can utilize the `initials` attribute of the template model
object to add or remove initials just like how we do for observables.

- `initials`: `Dict[str,Initials]`
    - The dictionary of initials in a template model

### Templates
Templates are stored in the `templates` attribute of template model objects

- `templates`: `List[Templates]`

Users can index on the list of templates or iterate throughout the list of templates to access templates. 

```python
from mira.examples.sir import sir

# access the second template using list indexing
template = sir.templates[1]

# go through all the templates in the model using a for loop
for template in sir.templates:
    pass
```

#### Template attributes
All template objects have 3 optional attributes
- `rate_law`: `Optional[SympyExprStr]`
  - The rate law that governs the template
- `name`: `Optional[str]`
  - The name of the template
- `display_name`: `Optional[str]`
  - An alternative name of the template
  
#### Template types
- Degradation
  - These templates represent the degradation of a species
  - They have the `subject` attribute
    - `subject`: `Concept`
      - The subject that is being degraded
- Production
  - These template represent the production of a species
  - They have the `outcome` attribute
    - `outcome`: `Concept`
      - The outcome that is being produced
- Conversion
  - These templates represent the conversion of one species to another
  - They have both the `subject` and `outcome` attributes
    - `subject`: `Concept`
      - The subject that is being converted
    - `outcome`: `Concept`
      - The result of the conversion

#### Template controllers
- Natural 
  - Specifies a process that occurs at a constant rate
- Controlled
  - Species a process controlled by a single controller
  - These templates have the `controller` attribute which represents a single compartment
    - `controller`: `Concept`
      - The controller that influence the template
- Group controlled
  - Species a process controlled by several controllers
  - These templates have the `controllers` attributes that represent a list of compartments
    - `controllers`: `List[Concept]`
      - The list of controllers that influence the template
      
#### Template operations

##### Template information retrieval


###### Getting all the concepts present in a template

We can extract all the concepts in template by using the `get_concepts` method.

- Documentation
  - `get_concepts() -> List[Union[Concept, List[Concept]]]`
    - Return the concepts present in a template

```python
from mira.examples.sir import sir

concepts_list = sir.templates[0].get_concepts()
```

###### Getting all the controllers present in a template

We can get all the controllers in a template by employing the `get_controllers` method.

- Documentation
  - `get_controllers() -> List[Concept]`
    - Return the controllers present in a template

```python
from mira.examples.sir import sir

controller_list = sir.templates[0].get_controllers()
```

##### Template modifications

###### Changing a template's rate-law

We can change the rate law of a template using the template instance method `set_rate_law`.

- Documentation
  - `set_rate_law(rate_law, local_dict)`
    - `rate_law`: `Union[str, sympy.Expr, SympyExprStr]`
      - The new rate law to use for a template
    - `local_dict`: `Optional[Dict[str,str]]`
      - An optional mapping of symbols to substitute into the new rate law
      
```python
from mira.examples.sir import sir

sir.templates[0].set_rate_law("I*beta")
```

###### Changing a parameter's name in a template's rate-law

We can update the names of parameters in a rate law using the template instance method `update_parameter_name`. 

- Documentation
  - `update_parameter_name(old_name, new_name)`
    - `old_name`: `str`
      - The old name of the parameter
    - `new_name`: `str`
      - The new name of the parameter

```python
from mira.examples.sir import sir

sir.templates[0].update_parameter_name("beta", "sigma")
```
## Template Model operations

### Adding a parameter

Users can use the `add_parameter` method which is a template model instance
method that adds a parameter
to the template model. The only required parameter is the id the parameter.

```python
from mira.examples.sir import sir

sir.add_parameter("mu")
```

- Documentation
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

If we added pet specific compartments to a human-centric SIR
  epidemiology model, but don't have accompanying parameters, we can add pet specific
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

If we had five different template models representing variations of the base SIR
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
under different circumstances.

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
# composed into a separate concepts
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
  method under arguments `concepts_to_stratify` and `params_to_stratify`.
    - `concepts_to_stratify`: `Optional[Collection[str]]`
        - The list of concept names that will be stratified
    -  `params_to_stratify`: `Optional[Collection[str]]`
        - The list of parameter names that will be stratified
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
to vaccinated; however, it's impossible once someone is vaccinated, to transition
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
city, since the infected population in one city will not
affect the infection of the susceptible population in another city.

```python
from mira.examples.sir import sir as model
from mira.metamodel.ops import stratify

key = "city"
strata = ["Boston", "Miami"]
stratify(model, key, strata, cartesian_control=False)
```