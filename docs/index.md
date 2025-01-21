# Interacting with MIRA template models using Python code

## Table of Contents
- [Templates](#templates)
  - [Get all concepts in a template](#get-all-the-concepts-present-in-a-template)
  - [Get all the controllers in a template](#get-all-the-controllers-present-in-a-template)
  - [Rewrite a template rate-law](#rewrite-a-template-rate-law)
  - [Rename a parameter in a template rate-law](#rename-a-parameter-in-a-template-rate-law)
- [Observables](#observables)
  - [Add an observable](#add-an-observable)
  - [Remove an observable](#remove-an-observable)
  - [Modify an observable expression](#modify-an-observable-expression)
- [Initials](#initials)
  - [Add an Initial](#add-an-initial)
  - [Remove an Initial](#remove-an-initial)
  - [Modify an initial expression](#modify-an-initial-expression)
    - [Use a number to represent an initial expressions](#set-an-initial-expression-to-a-number)
    - [Use an expression to represent an initial expression](#set-an-initial-expression-to-an-expression)
- [Template model operations](#template-model-operations)
  - [Add a parameter](#add-a-parameter)
  - [Retrieve concepts](#retrieve-concepts)
    - [Retrieve single concept by name](#retrieve-a-concept-by-name)
    - [Retrieve the concept map](#retrieve-the-concept-map)
  - [Add a template](#add-a-template)
    - [Add a template using add_template](#add-a-template-using-add_template)
    - [Add a template using add_transition](#add-a-template-using-add_transition)
    - [Append a template to the list of templates](#add-a-template-to-the-list-of-templates-stored-in-the-templates-attribute-of-a-template-model-object)
  - [Model stratification](#stratification)
    - [Select concepts and parameters to stratify](#select-concepts-and-parameters-to-stratify)
    - [Select concepts and parameters to preserve](#select-concepts-and-parameters-to-preserve)
    - [Rename concepts and parameters to include strata name](#rename-concepts-and-parameters)
    - [Add transition structure between strata](#add-transition-structure-between-strata)
      - [Stratify a model with no transition network structure](#stratify-a-model-with-no-transition-network-structure)
      - [Stratify a model with some transition network structure](#stratify-a-model-with-some-transition-network-structure)
    - [Split control based relationships on stratification](#split-control-based-relationships-on-stratification)
      - [Stratify a model while splitting control based relationships](#stratify-a-model-while-splitting-control-based-relationships)
      - [Stratify a model with no splitting of control based relationships](#stratify-a-model-with-no-splitting-of-control-based-relationships)
  - [Model composition](#composition)
    - [Compose variations of the same model](#compose-different-variations-of-the-same-model-into-one-comprehensive-model)
    - [Concept composition](#different-cases-of-concept-composition)



## Access model attributes

### Templates
Templates are stored in the `templates` attribute of template model objects

- `templates`: `List[Templates]`

Users can index on the list of templates or iterate throughout the list of templates to access templates. 

**Example: Accessing templates through list indexing and iteration**
```python
from mira.examples.sir import sir_petrinet as sir 

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

##### Retrieve template information


###### Get all the concepts present in a template

We can extract all the concepts in template by using the `get_concepts` method.

- Documentation
  - `get_concepts()`
    - Return type
      - `List[Union[Concept, List[Concept]]]`
        - A list of concepts present in the template

**Example: Return a list of all concepts in the template**
```python
from mira.examples.sir import sir_petrinet as sir 

concepts_list = sir.templates[0].get_concepts()
```


###### Get all the controllers present in a template 

We can get all the controllers in a template by employing the `get_controllers` method.

- Documentation
  - `get_controllers() -> List[Concept]`
    - Return type
      - `List[Concept]`
        - A list of controllers present in the template

**Example: Get all the controllers present in a template**
```python
from mira.examples.sir import sir_petrinet as sir 

controller_list = sir.templates[0].get_controllers()
```

##### Template modifications

###### Rewrite a template rate-law

We can change the rate law of a template using the template instance method `set_rate_law`.

- Documentation
  - `set_rate_law(rate_law, local_dict)`
    - `rate_law`: `Union[str, sympy.Expr, SympyExprStr]`
      - The new rate law to use for a template
    - `local_dict`: `Optional[Dict[str,str]]`
      - An optional mapping of symbols to substitute into the new rate law

**Example: Setting a custom rate-law for a template**
```python
from mira.metamodel.utils import SympyExprStr
from mira.examples.sir import sir_petrinet as sir 

sir.templates[0].set_rate_law(SympyExprStr("I*beta"))
```

###### Rename a parameter in a template rate-law

We can update the names of parameters in a rate law using the template instance method `update_parameter_name`. 

- Documentation
  - `update_parameter_name(old_name, new_name)`
    - `old_name`: `str`
      - The old name of the parameter
    - `new_name`: `str`
      - The new name of the parameter

**Example: Updating the parameter name in a template's rate-law**
```python
from mira.examples.sir import sir_petrinet as sir 

sir.templates[0].update_parameter_name("beta", "sigma")
```


### Observables

Observables associated with a template model can be accessed using the
`observables` attribute of a template model object.

- `observables`: `Dict[str,Observable]`
  - The dictionary of observables in a template model

#### Observable operations

- While we don't have any direct methods to add, remove, or modify observables,
  we can use the `observables` attribute to perform
  any observable specific operations.

##### Add an observable

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

**Example: Adding a single observable using key-based indexing**
```python
import sympy 

from mira.metamodel import *
from mira.examples.sir import sir_petrinet as sir 

key = "total_infections"
expression = sympy.Symbol("I")
total_infections_observable = Observable(name=key, expression=expression)

sir.observables[key] = total_infections_observable
```

Users can also add multiple observables at once using the Python dictionary
`update` method. The `update` method is a dictionary instance method that can
take in another dictionary and combines both dictionaries.

The passed-in dictionary takes priority and will overwrite the
key-value pairs of the original
dictionary if they share the same key.

**Example: Adding multiple observables using the dictionary update method**

```python
import sympy 

from mira.metamodel import *
from mira.examples.sir import sir_petrinet as sir 

key_infections = "total_infections"
expression_infections = sympy.Symbol("I")
total_infections_observable = Observable(name=key_infections,
                                         expression=expression_infections)

key_susceptible = "total_susceptible"
expression_susceptible = sympy.Symbol("S")
total_susceptible_observable = Observable(name=key_susceptible,
                                          expression=expression_susceptible)

new_observables = {key_infections: total_infections_observable,
                   key_susceptible: total_susceptible_observable}

sir.observables.update(new_observables)
```

##### Remove an observable

A user might want to remove an observable because it's no longer needed.

We can utilize the dictionary `pop` method that takes in a key and removes
the key-value pair from the dictionary if
it exists in the dictionary.

**Example: Removing an observable using the dictionary pop method**

```python
import sympy 

from mira.metamodel import *
from mira.examples.sir import sir_petrinet as sir 

key = "total_infections"
expression = sympy.Symbol("I")
total_infections_observable = Observable(name=key, expression=expression)

sir.observables[key] = total_infections_observable

sir.observables.pop(key)
```

##### Modify an observable expression

A user might want to modify the expression of an observable to keep track of a
different combination of compartments

We can use the Python dictionary method `get` on the observables dictionary which takes in a key and returns a
reference to the observable object
that we'd like to modify if its key exists in the `observables` dictionary.

**Example: Modifying the expression of an existing observable**
```python
import sympy 

from mira.metamodel import *
from mira.examples.sir import sir_petrinet as sir 

# Add the observable
key = "total_infections"
expression = sympy.Symbol("I")
total_infections_observable = Observable(name=key, expression=expression)

sir.observables[key] = total_infections_observable

# stratify to add a species specific strata for the infected compartment
model = stratify(sir, "species", ["human", "pet"], concepts_to_stratify=["I"])

# keep track of both human and pet infections for the total number of infected
sir.observables.get(key).expression = SympyExprStr("I_human+I_pet")
```

### Initials

Initials associated with a template model can be accessed using the `initials` attribute of a template model object. 


- `initials`: `Dict[str,Initials]`
  - The dictionary of initials in a template model

#### Initial operations
- Like observables, we don't have any direct methods to add, remove, or modify initials,
but we can utilize the `initials` attribute of the template model
object to add, remove, or modify initials just like how we do for observables.

##### Add an initial
A user might want to add a new initial to introduce a starting value for a compartment for simulation purposes. 

Users can define a key-value pair where the key represents the id of the initial and the value is a newly created initial object to add to the template model. We create a new initial object with name and expression to keep track of the total number of infected in a SIR epidemiology model.

If there already exists a key-value pair in the initial dictionary using the same key, then the old initial object will be overwritten by the new one.

**Example: Adding a single initial for the susceptible compartment in a SIR
model using key-based indexing**

```python
import sympy

from mira.metamodel import *
from mira.examples.sir import sir_petrinet as sir 

susceptible_concept = sir.get_concept("S")
key = susceptible_concept.name

# Though initial values for compartments can be numbers, the Python object type
# passed into the expression argument for the Initial constructor must be of type
# (SympyExprStr, sympy.Expr)
initial_expression = SympyExprStr(sympy.Float(1000))

# The Initial constructor takes in a concept object 
susceptible_initial = Initial(concept=susceptible_concept,
                              expression=initial_expression)

sir.initials[key] = susceptible_initial
```
Users can also add multiple initials at once using the Python dictionary update method. The update method is a dictionary instance method that can take in another dictionary and combines both dictionaries.

The passed-in dictionary takes priority and will overwrite the key-value pairs of the original dictionary if they share the same key.

**Example: Adding multiple initials using the dictionary update method**

```python
import sympy

from mira.metamodel import *
from mira.examples.sir import sir_petrinet as sir 

susceptible_concept = sir.get_concept("S")
infected_concept = sir.get_concept("I")
key_susceptible = susceptible_concept.name
key_infected = infected_concept.name 

susceptible_initial_expression = SympyExprStr(sympy.Float(1000))
infected_initial_expression = SympyExprStr(sympy.Float(0))

susceptible_initial = Initial(concept=susceptible_concept,
                              expression=susceptible_initial_expression)
infection_initial = Initial(concept=infected_concept,
                            expression=infected_initial_expression)

sir.initials[key_susceptible] = susceptible_initial
sir.initials[key_infected] = infection_initial


new_initials = {key_susceptible: susceptible_initial,
                   key_infected: infection_initial}

sir.initials.update(new_initials)
```

##### Remove an initial
A user might want to remove an initial because the compartment value it represents 
is no longer used for simulation purposes. 

We can utilize the dictionary `pop` method that takes in a key and removes the key-value pair from the dictionary if it exists in the dictionary.

**Example: Removing an initial using the dictionary pop method**
```python
import sympy

from mira.metamodel import *
from mira.examples.sir import sir_petrinet as sir 

susceptible_concept = sir.get_concept("S")
key_susceptible = susceptible_concept.name

susceptible_initial_expression = SympyExprStr(sympy.Float(5))
susceptible_initial = Initial(concept=susceptible_concept,
                              expression=susceptible_initial_expression)

sir.initials[key_susceptible] = susceptible_initial

sir.initials.pop(key_susceptible)
```

##### Modify an initial expression
A user might want to modify the initial of an expression to change the starting value for a compartment
during simulation. 

We can use the Python dictionary method `get` on the initials dictionary
which takes in a key and returns a reference to the initial object that we’d 
like to modify if its key exists in the `initials` dictionary.


There are two types of values that an initial object's expression can take. Users can either 
pass in a value or parameter to an initial expression to represent the initial value for a compartment. 

###### Set an initial expression to a number
Though we can use a number to represent the initial expression semantically, we must pass in 
a `sympy` object to the expression field for the Initial constructor. 

**Example: Setting the expression of an initial to be represented by a number**
```python
import sympy 

from mira.metamodel import *
from mira.examples.sir import sir_petrinet as sir 

susceptible_concept = sir.get_concept("S")

susceptible_initial = Initial(concept=susceptible_concept, 
                              expression=SympyExprStr(sympy.Float(1000)))
```
###### Set an initial expression to an expression
We can define the expression of an initial to be represented by an actual expression. 
  
**Example: Setting the expression of an initial to be represented by a parameter**
```python
from mira.metamodel import *
from mira.examples.sir import sir_petrinet as sir 

susceptible_concept = sir.get_concept("S")

# Add the parameter that represents the initial value for the susceptible compartment
# to the template model 
sir.add_parameter(parameter_id="S0", value=1000)

# Set the parameter "S0" to represent the initial value for the susceptible compartment
susceptible_initial = Initial(concept=susceptible_concept, 
                              expression=SympyExprStr("S0"))
```

## Template Model operations

### Retrieve concepts

There are multiple ways in which a user can retrieve concepts present in a template model object. We can either retrieve a single concept object by name or 
return a mapping of concept keys to concept objects. 

#### Retrieve a concept by name
We can use the `get_concept` method to return a single concept object. 

- Documentation
  - `get_concept(name)`
    - `name`: `str`
      - The concept name that represents the concept we want to retrieve
    - Return type
      - `Concept`
        - The specified concept
      - If there doesn't exist a concept in the template model with the name supplied to the method, 
      a `None`object will be returned. 

**Example: Retrieve a single concept object by name**
```python
from mira.examples.sir import sir_petrinet as sir 

susceptible_concept = sir.get_concept("S")
```

#### Retrieve the concept map 
If we want to retrieve all the concepts present in a template model, 
we can use the `get_concepts_map` method to return a mapping of concepts. 

- Documentation
  - `get_concepts_map()`
    - Return type
      - `Dict[str, Concept]`
        - The mapping of concepts

**Example: Return the mapping of concepts in a template model**
```python
from mira.examples.sir import sir_petrinet as sir

concepts_map = sir.get_concepts_map()
```

### Add a parameter

Users can use the `add_parameter` method which is a template model instance
method that adds a parameter
to the template model. The only required parameter is the id of the parameter.

**Example: Adding a parameter only using a parameter id to the template model**
```python
from mira.examples.sir import sir_petrinet as sir 

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

If we added pet-specific compartments to a human-centric SIR
  epidemiology model, but don't have accompanying parameters, we can add pet specific
  parameters with values for simulation purposes.

**Example: Add a new parameter with a value to the template model**
```python
from mira.examples.sir import sir_petrinet as sir 

sir.add_parameter("mu_pet", value=0.0003)
```

### Add a template

There are three ways that a template can be added to a template model object. A user
might want to add a template to an existing template model object to extend its capabilities or customize
the model to fit the specific problem scenario. 

#### Add a template using `add_template`
We can use the `add_template` template model instance method to add a template. 

- Documentation 
  - `add_template(template, parameter_mapping, initial_mapping)`
    - `template`: `Template`
      - The template to add to the template model 
    - `parameter_mapping`: `Optional[Mapping[str, Parameter]]`
      - A mapping of parameters that appear in the template to add to the template model 
    - `initial_mapping`: `Optional[Mapping[str,Initial]]`
      - A mapping of initials that appear in the template to add to the template model
    - Return type
      - `TemplateModel`
        - The template model with the new template added

**Example: Using the `add_template` method to add a template to the model**
```python
import sympy

from mira.examples.sir import sir_petrinet as sir
from mira.metamodel.templates import *
from mira.metamodel.template_model import *
from mira.metamodel.utils import SympyExprStr

recovered_concept = sir.get_concept("R")

# Define the template to add 
template = NaturalConversion(subject=recovered_concept,
                             outcome=sir.get_concept("I"),
                             rate_law=SympyExprStr("eta*R"))

# Add the new template "eta" that appears in the added rate law 
parameter_mapping = {"eta": Parameter(name="eta", value=5)}

# Update the initial for the recovered compartment 
initial_mapping = {"R": Initial(concept=recovered_concept,
                                 expression=SympyExprStr(sympy.Float(5)))}

sir.add_template(template, parameter_mapping=parameter_mapping,
                 initial_mapping=initial_mapping)
```

#### Add a template using `add_transition`
We can use the `add_transition` template model instance method to infer the template type to be added from
the arguments passed and add it to the template model. Currently, this  method only supports adding natural type templates. 

- Documentation 
  - `add_transition(transition_name, subject_concept, outcome_concept, rate_law_sympy, params_dict, mass_action_parameter)`
    - `transition_name`: `Optional[str]`
      - The name of the template 
    - `subject_concept`: `Optional[Concept]`
      - The subject of the template
    - `outcome_concept`: `Optional[Concept]`
      - The outcome of the template
    - `rate_law_sympy`: `Optional[SympyExprStr]`
      - The rate law that governs the template in sympy form
    - `params_dict`: `Optional[Mapping[str, Mapping[str,Any]]]`
      - The mapping of parameter names to their respective attributes to be added to the model
    - `mass_action_parameter`: `Optional[Parameter]`
      - The mass action parameter that will be set the template's mass action rate law if provided
    - Return type
      - `TemplateModel`
        - The template model with the new natural type template added 

**Example: Using the `add_transition` method to add a template to the model**
```python
import sympy 

from mira.examples.sir import sir_petrinet as sir
from mira.metamodel.utils import SympyExprStr

recovered_concept = sir.get_concept("I")
susceptible_concept = sir.get_concept("S")

rate_law_sympy = SympyExprStr(sympy.sympify("eta*R"))
params_dict = {"eta": {"display_name": "eta", "value": 5}}

sir.add_transition(subject_concept=recovered_concept, outcome_concept=susceptible_concept,
                   rate_law_sympy=rate_law_sympy, params_dict=params_dict)
```
    
#### Add a template to the list of templates stored in the `templates` attribute of a template model object
Rather than using a method, users can also add templates by directly appending a template to the `templates` attribute
which is a list of templates.

**Example: Adding a template directly accessing the `templates` attribute**
```python
from mira.examples.sir import sir_petrinet as sir
from mira.metamodel.templates import *
from mira.metamodel.utils import SympyExprStr

recovered_concept = sir.get_concept("R")

# Define the template to add 
template = NaturalConversion(subject=recovered_concept,
                             outcome=sir.get_concept("I"),
                             rate_law=SympyExprStr("eta*R"))

sir.templates.append(template)

# After the template it added, manually add the new parameter that appears in the template
sir.add_parameter(parameter_id="eta",value=.02)
```

### Stratification

The stratification method can take in an exhaustive list of arguments and
multiplies a template model into several strata.

The three required arguments are the input template model, key, and strata

**Example: Stratification on a basic SIR model by vaccination status**
```python
from mira.examples.sir import sir_petrinet as sir
from mira.metamodel.ops import stratify

key = "vaccination_status"
strata = ["unvaccinated", "vaccinated"]
sir = stratify(sir, key, strata)
```

- Documentation
  - `stratify(model, key, strata)`
    - `model`: `TemplateModel`
        - The input template model to be stratified
    - `key`:`str`
        - The singular name of the stratification
    - `strata`: `Collections[str]`
        - The list of values used for stratification
    - Return type
      - `TemplateModel`
        - The stratified template model 

#### Common use-cases

##### Select concepts and parameters to stratify

- If you want to not stratify certain parameters or concepts in the template
  model, you can pass in an optional collection of concept and parameter names
  to the stratify
  method under arguments `concepts_to_stratify` and `params_to_stratify`respectively.
    - `concepts_to_stratify`: `Optional[Collection[str]]`
        - The list of concept names that will be stratified
    -  `params_to_stratify`: `Optional[Collection[str]]`
        - The list of parameter names that will be stratified
    - If an argument isn't supplied, then all concepts and/or parameters will be
      stratified

**Example: Stratification on a SIR model while selecting certain concepts and parameters to stratify**
```python
from mira.examples.sir import sir_petrinet as sir 
from mira.metamodel.ops import stratify

key = "vaccination_status"
strata = ["unvaccinated", "vaccinated"]
sir = stratify(sir, key, strata, concepts_to_stratify=["S", "I"],
         params_to_stratify=["c", "beta", "m"])
```
##### Select concepts and parameters to preserve
- If the number of concepts and parameters that require stratification is too long, users can alternatively opt to 
  select the concepts and parameters they'd like to preserve from stratification. Users can pass in an optional
  collection of concept and parameter names to stratify method under arguments `concepts_to_preserve`
  and `parameters_to_preserve` respectively. 

  - `concepts_to_preserve`: `Optional[Collection[str]]`
    - The list of concept names to not stratify 
  - `parameters_to_preserve`: `Optional[Collection[str]]`
    - The list of parameter names to not stratify 
  -  If an argument isn't supplied, then all concepts and/or parameters will be
      stratified
  - Users aren't required to pass in both a collection of concepts/parameters to stratify and a collection of 
  concepts/parameters to preserve. Only one set of concepts/parameters are required. Any concepts/parameters
  not listed in the set of model attributes to preserve will be stratified. 

**Example: Stratification on a SIR model while selecting certain concepts and parameters to preserve**
```python
from mira.examples.sir import sir_petrinet as sir 
from mira.metamodel.ops import stratify

key = "vaccination_status"
strata = ["unvaccinated", "vaccinated"]
sir = stratify(sir, key, strata, concepts_to_preserve=["S", "I"],
         params_to_preserve=["c", "beta", "m"])
```


##### Rename concepts and parameters

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

**Example: Stratification on a SIR model while renaming specific compartment and parameters to include strata name**
```python
from mira.examples.sir import sir_petrinet as sir
from mira.metamodel.ops import stratify

key = "vaccination_status"
strata = ["unvaccinated", "vaccinated"]
sir = stratify(sir, key, strata, concepts_to_stratify=["S", "I"],
         params_to_stratify=["c", "beta", "m"],
         param_renaming_uses_strata_names=True,
         modify_names=True)
```

##### Add transition structure between strata

- If you wanted to specify certain pairs of compartments to have a directed
  transition structure where
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
              complete transition network structure between strata
            - If no structure is necessary, then pass in an empty list
          

###### Stratify a model with no transition network structure

An example where we wouldn't want any structure is if we were to stratify the
model by age. This is because for the purpose of modeling, people do not age.

**Example: Stratifying a SIR model by age with no transitions between strata** 
```python
from mira.examples.sir import sir_petrinet as sir
from mira.metamodel.ops import stratify

key = "age"
strata = ["under50", "50+"]
sir = stratify(sir, key, strata, structure=[])
```

###### Stratify a model with some transition network structure 

An example where we would want to specify some structure but not assume complete
transition network structure is if we
were to stratify a model based on vaccination status. This is because people can
transition from being unvaccinated
to vaccinated; however, it's impossible once someone is vaccinated, to transition
to unvaccinated.

We would pass in an iterable that contains a single tuple pair
`("unvaccinated", "vaccinated")` that represents
people getting vaccinated in a SIR epidemiological model.

 **Example: Stratifying a SIR model by vaccination status with some transitions between strata**
```python
from mira.examples.sir import sir_petrinet as sir
from mira.metamodel.ops import stratify

key = "vaccination_status"
strata = ["unvaccinated", "vaccinated"]
sir = stratify(sir, key, strata, structure=[("unvaccinated", "vaccinated")])
```

##### Split control based relationships on stratification

- Setting the `cartesian_control` argument to true will split all control based
  relationships based on the stratification.
    - `cartesian_control`: `Optional[bool]`
        - Setting this to true splits all control relationships in the model


###### Stratify a model while splitting control based relationships

The `cartesian_control` argument should be set to true for a SIR epidemiology model stratified on
age. As the transition from the susceptible
to the infected compartment for a certain age group is controlled by the
infected compartment of other age groups.

**Example: Stratifying a SIR model by age while splitting control based relationships**
```python
from mira.examples.sir import sir_petrinet as sir
from mira.metamodel.ops import stratify

key = "age"
strata = ["under50", "50+"]
sir = stratify(sir, key, strata, cartesian_control=True)
```

###### Stratify a model with no splitting of control based relationships

We would set `cartesian_control` to false for a SIR epidemiology model based on
city, since the infected population in one city will not
affect the infection of the susceptible population in another city.

**Example: Stratifying a SIR model by city with no splitting of control based relationships**
```python
from mira.examples.sir import sir_petrinet as sir
from mira.metamodel.ops import stratify

key = "city"
strata = ["Boston", "Miami"]
sir = stratify(sir, key, strata, cartesian_control=False)
```

### Composition

The composition method takes in a list of template models and composes them into
a single
template model. The list must contain at least two template models.

**Example: Compose a list of two SIR based epidemiological models**
```python
from mira.examples.sir import sir, sir_2_city
from mira.metamodel.composition import compose

tm_list = [sir, sir_2_city]
composed_tm = compose(tm_list)
```
- Documentation
  - `tm_list`: `List[TemplateModel]`
    - A list of template models to be composed
  - Return type
    - `TemplateModel`
      - The composed template model 

The composition functionality prioritizes template model attributes (parameters,
initials, templates, annotation, time, model time, etc.)
of the first template model in the list.

#### Common use-cases

##### Compose different variations of the same model into one comprehensive model
If we had five different template models representing variations of the base SIR
epidemiological model, we can combine them using model composition.

**Example: Compose five different SIR based models**
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

##### Different cases of concept composition

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

##### **Example: Different types of concept composition examples**

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
