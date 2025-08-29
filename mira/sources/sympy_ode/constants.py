from string import Template


ODE_IMAGE_PROMPT = """Transform these equations into a sympy representation based on the example style below

```python
# Define time variable
t = sympy.symbols("t")

# Define the time-dependent variables
S, E, I, R = sympy.symbols("S E I R", cls=sympy.Function)

# Define the parameters
b, g, r = sympy.symbols("b g r")

odes = [
    sympy.Eq(S(t).diff(t), - b * S(t) * I(t)),
    sympy.Eq(E(t).diff(t), b * S(t) * I(t) - r * E(t)),
    sympy.Eq(I(t).diff(t), r * E(t) - g * I(t)),
    sympy.Eq(R(t).diff(t), g * I(t))
]
```

Instead of using unicode characters, spell out in symbols in lowercase like theta, omega, etc.
Also, provide the code snippet only and no explanation."""

ODE_CONCEPTS_PROMPT_TEMPLATE = Template("""
I want to annotate epidemiology models with attributes that describes the identity and context of each compartment.

An example is the set of ODE equations below, and the corresponding context data:

odes = [
    sp.Eq(S_l(t).diff(t), pi_h * (1 - rho) - nu * lambda_h * S_l(t) - mu_h * S_l(t)),
    sp.Eq(S_h(t).diff(t), pi_h * rho - lambda_h * S_h(t) - mu_h * S_h(t)),
    sp.Eq(E_h(t).diff(t), nu * S_l(t) * lambda_h + S_h(t) * lambda_h - (sigma_h + mu_h) * E_h(t)),
    sp.Eq(P(t).diff(t), sigma_h * E_h(t) - (omega + mu_h) * P(t)),
    sp.Eq(I1(t).diff(t), omega * P(t) - (theta + k1 + tau1 + mu_h) * I1(t)),
    sp.Eq(I2(t).diff(t), theta * I1(t) - (k2 + delta_i + tau2 + mu_h) * I2(t)),
    sp.Eq(H(t).diff(t), k1 * I1(t) + k2 * I2(t) - (delta_h + tau3 + mu_h) * H(t)),
    sp.Eq(R_h(t).diff(t), tau1 * I1(t) + tau2 * I2(t) + tau3 * H(t) - mu_h * R_h(t)),
    sp.Eq(S_r(t).diff(t), pi_r - lambda_r * S_r(t) - mu_r * S_r(t)),
    sp.Eq(E_r(t).diff(t), lambda_r * S_r(t) - (sigma_r + mu_r) * E_r(t)),
    sp.Eq(I_r(t).diff(t), sigma_r * E_r(t) - (delta_r + tau_r + mu_r) * I_r(t)),
    sp.Eq(R_r(t).diff(t), tau_r * I_r(t) - mu_r * R_r(t)),
]

concept_data = {
    'S_l': {'identifiers': {'ido': '0000514'},
            'context': {'severity': 'low', 'species': 'ncbitaxon:9606'}},
    'S_h': {'identifiers': {'ido': '0000514'},
            'context': {'severity': 'high', 'species': 'ncbitaxon:9606'}},
    'E_h': {'identifiers': {'apollosv': '00000154'},
            'context': {'species': 'ncbitaxon:9606'}},
    'P': {'identifiers': {'ido': '0000511'},
          'context': {'stage': 'predromal', 'species': 'ncbitaxon:9606'}},
    'I1': {'identifiers': {'ido': '0000511'},
           'context': {'stage': 'mild', 'species': 'ncbitaxon:9606'}},
    'I2': {'identifiers': {'ido': '0000511'},
           'context': {'stage': 'severe', 'species': 'ncbitaxon:9606'}},
    'H': {'identifiers': {'ido': '0000511'},
         'context': {'hospitalization': 'ncit:C25179', 'species': 'ncbitaxon:9606'}},
    'R_h': {'identifiers': {'ido': '0000592'},
         'context': {'species': 'ncbitaxon:9606'}},
    'S_r': {'identifiers': {'ido': '0000514'},
            'context': {'species': 'ncbitaxon:9989'}},
    'E_r': {'identifiers': {'apollosv': '00000154'},
            'context': {'species': 'ncbitaxon:9989'}},
    'I_r': {'identifiers': {'ido': '0000511'},
           'context': {'species': 'ncbitaxon:9989'}},
    'R_r': {'identifiers': {'ido': '0000592'},
            'context': {'species': 'ncbitaxon:9989'}},
}

Now look at the following equations and give me the corresponding concept data:

$ode_insert

Below, there are many more examples of how we annotate various commonly occurring compartments:

{'Ailing': {'identifiers': {'ido': '0000511'},
  'context': {'disease_severity': 'ncit:C25269', 'diagnosis': 'ncit:C113725'}},
 'asymptomatic': {'identifiers': {'ido': '0000511'},
  'context': {'disease_severity': 'ncit:C3833'}},
 'Asymptomatic': {'identifiers': {'ido': '0000511'},
  'context': {'disease_severity': 'ncit:C3833'}},
 'Confirmed': {'identifiers': {'ido': '0000511'},
  'context': {'diagnosis': 'ncit:C15220'}},
 'Confirmed_Infected': {'identifiers': {'ido': '0000511'},
  'context': {'diagnosis': 'ncit:C15220'}},
 'dead_corona_nontested': {'identifiers': {'ncit': 'C28554'},
  'context': {'diagnosis': 'ncit:C113725', 'cause_of_death': 'ncit:C171133'}},
 'dead_corona_tested': {'identifiers': {'ncit': 'C28554'},
  'context': {'diagnosis': 'ncit:C15220', 'cause_of_death': 'ncit:C171133'}},
 'dead_noncorona': {'identifiers': {'ncit': 'C28554'},
  'context': {'cause_of_death': 'ncit:C17649'}},
 'deceased': {'identifiers': {'ncit': 'C28554'}, 'context': {}},
 'Deceased': {'identifiers': {'ncit': 'C28554'}, 'context': {}},
 'Deceased_Counties_neighbouring_counties_with_airports': {'identifiers': {'ncit': 'C28554'},
  'context': {'county_property': 'neighbouring_counties_with_airports'}},
 'Deceased_Counties_with_airports': {'identifiers': {'ncit': 'C28554'},
  'context': {'county_property': 'with_airports'}},
 'Deceased_Counties_with_highways': {'identifiers': {'ncit': 'C28554'},
  'context': {'county_property': 'with_highways'}},
 'Deceased_Low_risk_counties': {'identifiers': {'ncit': 'C28554'},
  'context': {'county_property': 'low_risk'}},
 'detected': {'identifiers': {'ido': '0000511'},
  'context': {'diagnosis': 'ncit:C15220'}},
 'Diagnosed': {'identifiers': {'ido': '0000511'},
  'context': {'diagnosis': 'ncit:C15220'}},
 'Discharged_Counties_neighbouring_counties_with_airports': {'identifiers': {'ido': '0000592'},
  'context': {'hospitalization': 'ncit:C154475',
   'county_property': 'neighbouring_counties_with_airports'}},
 'Discharged_Counties_with_airports': {'identifiers': {'ido': '0000592'},
  'context': {'hospitalization': 'ncit:C154475',
   'county_property': 'with_airports'}},
 'Discharged_Counties_with_highways': {'identifiers': {'ido': '0000592'},
  'context': {'hospitalization': 'ncit:C154475',
   'county_property': 'with_highways'}},
 'Discharged_Low_risk_counties': {'identifiers': {'ido': '0000592'},
  'context': {'hospitalization': 'ncit:C154475',
   'county_property': 'low_risk'}},
 'exposed': {'identifiers': {'apollosv': '00000154'}, 'context': {}},
 'Exposed': {'identifiers': {'apollosv': '00000154'}, 'context': {}},
 'Exposed_quarantined': {'identifiers': {'apollosv': '00000154'},
  'context': {'quarantined': 'ncit:C71902'}},
 'Extinct': {'identifiers': {'ncit': 'C28554'}, 'context': {}},
 'Fatalities': {'identifiers': {'ncit': 'C28554'}, 'context': {}},
 'Healed': {'identifiers': {'ido': '0000592'}, 'context': {}},
 'Hospitalised': {'identifiers': {'ido': '0000511'},
  'context': {'hospitalization': 'ncit:C25179'}},
 'Hospitalised_Counties_neighbouring_counties_with_airports': {'identifiers': {'ido': '0000511'},
  'context': {'hospitalization': 'ncit:C25179',
   'county_property': 'neighbouring_counties_with_airports',
   'icu': 'ncit:C68851'}},
 'Hospitalised_Counties_with_airports': {'identifiers': {'ido': '0000511'},
  'context': {'hospitalization': 'ncit:C25179',
   'county_property': 'with_airports',
   'icu': 'ncit:C68851'}},
 'Hospitalised_Counties_with_highways': {'identifiers': {'ido': '0000511'},
  'context': {'hospitalization': 'ncit:C25179',
   'county_property': 'with_highways',
   'icu': 'ncit:C68851'}},
 'Hospitalised_Low_risk_counties': {'identifiers': {'ido': '0000511'},
  'context': {'hospitalization': 'ncit:C25179',
   'county_property': 'low_risk',
   'icu': 'ncit:C68851'}},
 'Hospitalized': {'identifiers': {'ido': '0000511'},
  'context': {'hospitalization': 'ncit:C25179',
   'disease_severity': 'ncit:C25269'}},
 'ICU_Counties_neighbouring_counties_with_airports': {'identifiers': {'ido': '0000511'},
  'context': {'hospitalization': 'ncit:C25179',
   'icu': 'ncit:C53511',
   'county_property': 'neighbouring_counties_with_airports'}},
 'ICU_Counties_with_airports': {'identifiers': {'ido': '0000511'},
  'context': {'hospitalization': 'ncit:C25179',
   'icu': 'ncit:C53511',
   'county_property': 'with_airports'}},
 'ICU_Counties_with_highways': {'identifiers': {'ido': '0000511'},
  'context': {'hospitalization': 'ncit:C25179',
   'icu': 'ncit:C53511',
   'county_property': 'with_highways'}},
 'ICU_Low_risk_counties': {'identifiers': {'ido': '0000511'},
  'context': {'hospitalization': 'ncit:C25179',
   'icu': 'ncit:C53511',
   'county_property': 'low_risk'}},
 'Infected': {'identifiers': {'ido': '0000511'}, 'context': {}},
 'Infected_Asymptomatic': {'identifiers': {'ido': '0000511'},
  'context': {'disease_severity': 'ncit:C3833'}},
 'Infected_Counties_neighbouring_counties_with_airports': {'identifiers': {'ido': '0000511'},
  'context': {'county_property': 'neighbouring_counties_with_airports'}},
 'Infected_Counties_with_airports': {'identifiers': {'ido': '0000511'},
  'context': {'county_property': 'with_airports'}},
 'Infected_Counties_with_highways': {'identifiers': {'ido': '0000511'},
  'context': {'county_property': 'with_highways'}},
 'Infected_Low_risk_counties': {'identifiers': {'ido': '0000511'},
  'context': {'county_property': 'low_risk'}},
 'infected_nontested': {'identifiers': {'ido': '0000511'},
  'context': {'diagnosed': 'ncit:C113725'}},
 'Infected_quarantined': {'identifiers': {'ido': '0000511'},
  'context': {'quarantined': 'ncit:C71902'}},
 'Infected_reported': {'identifiers': {'ido': '0000511'},
  'context': {'diagnosis': 'ncit:C15220'}},
 'Infected_strong_immune_system': {'identifiers': {'ido': '0000511'},
  'context': {'immune_system': 'ncit:C62223'}},
 'Infected_Symptomatic': {'identifiers': {'ido': '0000511'},
  'context': {'disease_severity': 'ncit:C25269'}},
 'infected_tested': {'identifiers': {'ido': '0000511'},
  'context': {'diagnosis': 'ncit:C15220'}},
 'Infected_unreported': {'identifiers': {'ido': '0000511'},
  'context': {'diagnosed': 'ncit:C113725'}},
 'Infected_weak_immune_system': {'identifiers': {'ido': '0000511'},
  'context': {'immune_system': 'ncit:C62224'}},
 'Infectious': {'identifiers': {'ido': '0000511'},
  'context': {'transmissibility': 'ncit:C25376'}},
 'Pathogen': {'identifiers': {'ncit': 'C80324'}, 'context': {}},
 'Quarantined': {'identifiers': {'ido': '0000511'},
  'context': {'quarantined': 'ncit:C71902'}},
 'Quarantined_Infected': {'identifiers': {'ido': '0000511'},
  'context': {'quarantined': 'ncit:C71902'}},
 'Recognized': {'identifiers': {'ido': '0000511'},
  'context': {'diagnosis': 'ncit:C15220'}},
 'recovered': {'identifiers': {'ido': '0000592'}, 'context': {}},
 'Recovered': {'identifiers': {'ido': '0000592'}, 'context': {}},
 'Recovered_Counties_neighbouring_counties_with_airports': {'identifiers': {'ido': '0000592'},
  'context': {'county_property': 'neighbouring_counties_with_airports'}},
 'Recovered_Counties_with_airports': {'identifiers': {'ido': '0000592'},
  'context': {'county_property': 'with_airports'}},
 'Recovered_Counties_with_highways': {'identifiers': {'ido': '0000592'},
  'context': {'county_property': 'with_highways'}},
 'Recovered_Low_risk_counties': {'identifiers': {'ido': '0000592'},
  'context': {'county_property': 'low_risk'}},
 'recovered_nontested': {'identifiers': {'ido': '0000592'},
  'context': {'diagnosis': 'ncit:C113725'}},
 'recovered_tested': {'identifiers': {'ido': '0000592'},
  'context': {'diagnosis': 'ncit:C15220'}},
 'Removed': {'identifiers': {'ido': '0000592'}, 'context': {}},
 'Super_spreaders': {'identifiers': {'ido': '0000511'},
  'context': {'transmissibility': 'ncit:C49508'}},
 'Susceptible': {'identifiers': {'ido': '0000514'}, 'context': {}},
 'susceptible': {'identifiers': {'ido': '0000514'}, 'context': {}},
 'Susceptible_confined': {'identifiers': {'ido': '0000514'},
  'context': {'quarantined': 'ncit:C71902'}},
 'Susceptible_Counties_neighbouring_counties_with_airports': {'identifiers': {'ido': '0000514'},
  'context': {'county_property': 'neighbouring_counties_with_airports'}},
 'Susceptible_Counties_with_airports': {'identifiers': {'ido': '0000514'},
  'context': {'county_property': 'with_airports'}},
 'Susceptible_Counties_with_highways': {'identifiers': {'ido': '0000514'},
  'context': {'county_property': 'with_highways'}},
 'Susceptible_isolated': {'identifiers': {'ido': '0000514'},
  'context': {'quarantined': 'ncit:C71902'}},
 'Susceptible_Low_risk_counties': {'identifiers': {'ido': '0000514'},
  'context': {'county_property': 'low_risk'}},
 'Susceptible_quarantined': {'identifiers': {'ido': '0000514'},
  'context': {'quarantined': 'ncit:C71902'}},
 'Susceptible_unconfined': {'identifiers': {'ido': '0000514'},
  'context': {'quarantined': 'ncit:C68851'}},
 'symptomatic': {'identifiers': {'ido': '0000511'},
  'context': {'disease_severity': 'ncit:C25269'}},
 'symptoms_nontested': {'identifiers': {'ido': '0000511'},
  'context': {'disease_severity': 'ncit:C25269', 'diagnosed': 'ncit:C113725'}},
 'symptoms_tested': {'identifiers': {'ido': '0000511'},
  'context': {'disease_severity': 'ncit:C25269', 'diagnosis': 'ncit:C15220'}},
 'Threatened': {'identifiers': {'ido': '0000511'},
  'context': {'disease_severity': 'ncit:C25467'}},
 'Total_population': {'identifiers': {'ido': '0000509'}, 'context': {}},
 'uninfected_nontested': {'identifiers': {'ido': '0000514'},
  'context': {'diagnosis': 'ncit:C113725'}},
 'uninfected_tested': {'identifiers': {'ido': '0000514'},
  'context': {'diagnosis': 'ncit:C15220'}},
 'Unquarantined_Infected': {'identifiers': {'ido': '0000511'},
  'context': {'quarantined': 'ncit:C68851'}}}

Please only respond with the code snippet defining the concept data"
""")


ERROR_CHECKING_PROMPT = """
You are an error checker for MIRA ODE extractions. Review the following extraction:

Code:
{code}

Concept Data:
{concepts}


Follow these steps for checking the errors and correct the errors based on these guidlines:
1. Execution errors
  - Check missing imports, undefined variables, syntax errors
  Required imports: Symbol, Function, Eq, Derivative from sympy
  - Check for namespace conflicts (avoid mixing 'import sympy' with 'from sympy import *')
  - Verify all used functions are imported (exp, log, sin, cos, etc.)

    **CRITICAL**: If you find undefined variables:
      - First check if it's a typo of an existing variable
      - If not a typo, determine from context if it should be:
        - A Symbol (constant parameter)
        - A Function (time-varying state variable)
      - Add the definition BEFORE its first use
      - If still unclear, analyze the equation structure to infer the type

    SYNTAX validation
      - Check for Python syntax errors (missing colons, parentheses, etc.)
      - Verify SymPy expression syntax (proper use of operators)
      - Ensure no string literals where symbols are expected

2. Parameter consistency (all parameters defined and used correctly)
  - Parameter definition:
    **Symbol vs Function vs Derivative - CRITICAL DISTINCTIONS:**

    **Use Symbol for:**
      - Rate constants (beta, gamma, mu, alpha, etc.)
      - Fixed parameters (N, K, R0, etc.)
      - Initial conditions when defined as constants
      - Definition: `beta = Symbol('beta', positive=True, real=True)`

    **Use Function for:**
      - ANY variable that appears with d/dt in equations
      - State variables (S, I, R, x, y, etc.)
      - Time-varying quantities
      - Definition: `S = Function('S')` then use as `S(t)` in equations

    **NEVER DO:**
      - `Symbol('S')(t)` - Symbols are NOT callable
      - `Function('S')` without `(t)` when using in equations
      - Mix Symbol and Function for the same variable

  - Parameter consistency check:
    - Every parameter in equations must be defined
    - No parameters defined but unused (clean up redundant definitions)
    - Parameter attributes consistency (if beta is positive in one place, should be everywhere)

  AUTO-FIX STRATEGY for parameters:
  If parameter P is undefined:
  - First check if P appears with derivative → make it Function('P')
  - Check if P is used as constant → make it Symbol('P')
  - Check equation context:
    - If P(t) appears → Function
    - If dP/dt appears → Function
    - If P appears alone in algebraic operations → Symbol
  - Add appropriate definition in correct section of code

3. Time dependency issues (variables with d/dt properly defined as functions)
  - Derivative pattern detection:
    Scan for these patterns to identify what should be Functions:
    - `Derivative(X, t)` or `X.diff(t)` → X must be Function
    - `dX/dt` in comments → X should be Function
    - Differential equation left side → always Function

  - Time dependent variable rules:
    Exmaples for correct patterns:
      S = Function('S')
      equation = Eq(Derivative(S(t), t), -beta*S(t)*I(t))
    Examples for incorrect patterns to fix:
      S = Symbol('S')
      Eq(Derivative(S, t), ...)
      Eq(S.diff(t), ...)  # if S is Symbol

  - Function usage consistency:
    - If X is defined as Function('X'), ALWAYS use X(t) in equations
    - Never use bare X without (t) for Functions in mathematical expressions
    - Initial conditions: X(0) not X_0 for time-dependent variables

  AUTO-CORRECTION ALGORITHM:
    - First identify all variables in Derivative(..., t)
    - Ensure these are defined as Function not Symbol
    - Replace all instances: if fixing S = Symbol('S') to S = Function('S'):
      - In derivatives: already correct
      - In equations: change S to S(t)
      - In initial conditions: use S(0)


4. Concept grounding accuracy (concept_data matches the variables in equations)
  - Variable concept-mapping:
    - Every Symbol/Function in code must have concept entry
    - Concept names must match variable names exactly
    - No extra concepts without corresponding variables

  - Concept-type validation:
    Match concept types to variable usage:
    - State variables (with d/dt) → population/compartment concepts
    - Rate parameters → rate/probability concepts  
    - Constants → parameter/initial condition concepts

  - Bidirectional consistency:
    Check both directions:
    1. Code → Concepts: Every variable has a concept
    2. Concepts → Code: Every concept has a variable
    3. Flag orphaned entries in either direction

HOW TO FIX COMMON ERRORS:
1. Missing imports → Add at the top:
   from sympy import Symbol, Function, Eq, Derivative

2. Symbol vs Function errors → 
   - If variable has d/dt, change: S = Symbol('S') → S = Function('S')
   - Then use S(t) everywhere in equations

3. Undefined parameters →
   - Add after time definition: beta, gamma = sympy.symbols('beta gamma')

4. NameError for variables →
   - Check if it's a typo (xy vs xy1)
   - Add definition before first use

When fixing Symbol vs Function errors:
1. Find ALL variables that appear in derivatives
2. Change ALL of them from Symbol to Function in one go
3. Update ALL their usages to include (t)
Example fix:
   # WRONG:
   S, E, I, R = symbols('S E I R')
   
   # CORRECT:
   from sympy import Function
   S = Function('S')
   E = Function('E')
   I = Function('I')
   R = Function('R')

CRITICAL RULE FOR ODE SYSTEMS:
In systems of ordinary differential equations (ODEs):
- ANY variable that appears with .diff(t) or d/dt on the LEFT side of an equation MUST be defined as Function, not Symbol
- These are STATE VARIABLES (compartments in epidemiological models) that change over time
- Common compartment variables: S, E, I, R, A, P, H, F, V, T, Q, D, C, etc.
- These MUST be defined as: S = Function('S'), E = Function('E'), etc.
- Then use them as S(t), E(t), etc. in ALL equations

Only use Symbol for:
- Rate parameters (beta, gamma, mu, alpha, sigma, etc.)
- Constants (N for total population if constant, k, R0, etc.)
- Variables that NEVER appear with d/dt

AUTOMATIC FIX RULE:
If you see any of these patterns, the variable MUST be a Function:
- X(t).diff(t) in any equation → X = Function('X')
- Derivative(X(t), t) → X = Function('X')

When returning corrected_code:
- Include ALL imports needed
- Include ALL variable definitions
- Include the complete odes list

Output format:
If you find errors, return a JSON with:
{{
    "has_errors": true,
    "errors": {{
        "execution_errors": ["Missing import: Function", "NameError: 'xy' is not defined"],
        "parameter_errors": ["'Symbol' object is not callable for S(t)", "beta used but not defined"],
        "time_dependency_errors": ["S appears in derivative but defined as Symbol instead of Function"],
        "concept_errors": ["Variable 'gamma' has no concept entry", "Concept 'R' has no corresponding variable"]
    }},
    "auto_fixes_applied": [
        "Added: xy = Symbol('xy', positive=True) based on usage context",
        "Changed: S = Symbol('S') → S = Function('S') due to derivative",
        "Fixed: All S instances changed to S(t) in equations",
        "Added: Missing import for Function"
    ],
    "corrected_code": "# COMPLETE fixed sympy code with all imports",
    "corrected_concepts": "# Fixed concept_data if needed",
    "confidence": "high/medium/low",
    "manual_review_needed": ["List any ambiguous fixes that may need human review"]
}}

- For "corrected_concepts": ALWAYS return a dictionary object {}, NEVER a string or comment
- If no changes are needed to concepts, return the original concept_data as a dictionary {}

ALWAYS return valid JSON only!

"""
