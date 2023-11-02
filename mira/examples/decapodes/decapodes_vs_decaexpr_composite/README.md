# Decapodes vs DecaExpr Composite models

This directory contains the components of the composite model example at 
https://algebraicjulia.github.io/SyntacticModels.jl/dev/generated/composite_models_examples/

## DecaExpr JSON files

The DecaExpr JSON files are generated from the full composite JSON output found in the link above by running the 
following code (in Python)

```python
from mira.metamodel.decpodes_examples import get_composite_example_json
import json

composite_example_json = get_composite_example_json()

with open('oscillator_decaexpr.json', 'w') as f:
    json.dump(fp=f, obj=composite_example_json['components'][0]['model'])

with open('friction_decaexpr.json', 'w') as f:
    json.dump(fp=f, obj=composite_example_json['components'][1]['model'])
```

## Decapodes JSON files

The decapodes JSON files are generated from the DecaExpr julia models files by running the following code (in julia). 
To run this code, julia has to be installed. Then the dependencies need to be installed as well. julia is pretty 
explicit about what needs to be installed, so if you have julia installed and try to run this code, it will tell you 
what needs to be installed if any dependencies are missing and how to do it. Typically, it involves running 
`import Pkg; Pkg.add("PackageName")` in the julia REPL.

```julia
# The code here mostly follows the code in
# https://algebraicjulia.github.io/SyntacticModels.jl/dev/generated/composite_models_examples/ 

using SyntacticModels

using SyntacticModels.AMR
using SyntacticModels.ASKEMDecapodes
using SyntacticModels.ASKEMUWDs
using SyntacticModels.Composites

using MLStyle
import SyntacticModels.ASKEMDecapodes.Decapodes as Decapodes
using Catlab
using Catlab.RelationalPrograms
using Catlab.WiringDiagrams
using Test
using JSON3

# Import Decapodes to access SummationDecapode; Avoid name collision
import Decapodes as DecapodesModule

# Specifying the Composition Pattern
x = Typed(:X, :Form0)
v = Typed(:V, :Form0)
Q = Typed(:Q, :Form0)
variables = [x,v,Q]

c = [x, Q]
s = [Statement(:oscillator, [x,v]),
     Statement(:heating, [v,Q])]
u = ASKEMUWDs.UWDExpr(c, s)

# Specifying the Component Systems
h = AMR.Header(
    "harmonic_oscillator",
    "modelreps.io/DecaExpr",
    "A Simple Harmonic Oscillator as a Diagrammatic Equation",
    "DecaExpr",
    "v1.0"
)
 
dexpr = Decapodes.parse_decapode(quote
    X::Form0{Point}
    V::Form0{Point}

    k::Constant{Point}

    ∂ₜ(X) == V
    ∂ₜ(V) == -1*k*(X)
end
)

# Model 1
d1 = ASKEMDecaExpr(h, dexpr)

# Model 2
d2 = ASKEMDecaExpr(
  AMR.Header("fricative_heating",
   "modelreps.io/SummationDecapode",
   "Velocity makes it get hot, but you dissipate heat away from Q₀",
   "SummationDecapode", "v1.0"),
    Decapodes.parse_decapode(quote
      V::Form0{Point}
      Q::Form0{Point}
      κ::Constant{Point}
      λ::Constant{Point}
      Q₀::Parameter{Point}

      ∂ₜ(Q) == κ*V + λ(Q - Q₀)
    end)
)

# Create a header for the decpode version of model 1
decpode1_header = AMR.Header(
    "harmonic_oscillator",
    "modelreps.io/SummationDecapode",
    "A Simple Harmonic Oscillator",
    "SummationDecapode",
    "v1.0"
)

# Create the decpode version of model 1
# The transformation from DecaExpr to Decapode is done by the SummationDecapode function on the model
d1_decapode = ASKEMDecapode(decpode1_header, DecapodesModule.SummationDecapode(d1.model))

# Repeat for model 2
decpode2_header = AMR.Header(
    "fricative_heating",
    "modelreps.io/SummationDecapode",
    "Velocity makes it get hot, but you dissipate heat away from Q₀",
    "SummationDecapode",
    "v1.0"
)
d2_decapode = ASKEMDecapode(decpode2_header, DecapodesModule.SummationDecapode(d2.model))

# Write the decapode JSON files
write_json_acset(d1_decapode.model, "d1_oscillator_decapode.json")
write_json_acset(d2_decapode.model, "d2_friction_decapode.json")
```
