from string import Template

ODE_CHANGE_PROMPT = Template("""
You are editing a Python code snippet that defines a system of ODEs using
sympy. The snippet was parsed into a compartmental model, and during parsing
the following changes had to be applied to make the model valid. The snippet
itself was not updated, so it no longer describes the model that was built.
 
Rewrite the snippet so that it describes the model as built.
 
Changes that were applied:
$changes
 
Current snippet:
```python
$ode_str
```
 
Rules:
- Apply only the edits listed above. Change nothing else.
- Keep the same state variables, the same number of equations, and the same
  order of equations.
- Do not rename anything, do not introduce new parameters, and do not
  simplify, expand, or otherwise rearrange the equations.
- The snippet must still define a variable named `odes` holding a list of
  sympy.Eq objects.
- Keep any imports the snippet needs.
- Return only the Python code, with no explanation and no markdown fences.

$feedback
Attempt $attempt of $max_attempts.
""")


FEEDBACK_PROMPT = Template("""
Your previous attempt was rejected for this reason:
$error
 
Previous attempt:
```python
$previous
```
""")

ODE_IMAGE_PROMPT = """You will be given a single image containing equations from a scientific paper.
Transform the ODE system in the image into a SymPy representation following this exact style:

import sympy

t = sympy.symbols("t")

S, E, I, R = sympy.symbols("S E I R", cls=sympy.Function)

b, g, r = sympy.symbols("b g r")

odes = [
    sympy.Eq(S(t).diff(t), -b * S(t) * I(t)),
    sympy.Eq(E(t).diff(t), b * S(t) * I(t) - r * E(t)),
    sympy.Eq(I(t).diff(t), r * E(t) - g * I(t)),
    sympy.Eq(R(t).diff(t), g * I(t))
]

IGNORE equations that are:
- Simple definitions or substitutions (e.g., Q → C, N = S + I + R)
- Error/loss/objective functions (e.g., err = ||C - Ĉ||₂)
- Normalisation constraints (e.g., S + E + I + R = N)
- Integral or cumulative forms (e.g., C(t) = ∫ I(τ)dτ)
- Discrete-time recurrences (e.g., I_{n+1} = ...)
- Single variable definitions without derivatives
- Equations that appear truncated or partially visible in the image

Symbol naming rules:
- Never use Greek or other unicode characters directly
- Spell out Greek letters in lowercase: beta, gamma, mu, theta, omega, etc.
- Subscripts become suffixes: β₁ → beta1, γ_eff → gamma_eff
- If a symbol is ambiguous due to image quality, choose the most epidemiologically
  conventional interpretation (e.g., prefer `mu` over `u` for a Greek-looking character)
- Use short alphanumeric names only

Output rules:
- Begin with `import sympy` and nothing else before it
- Output raw Python only — no markdown fences, no explanation, no preamble
- If no valid ODE system is found, output only: odes = []
"""


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

Please only respond with the code snippet defining the concept data.
""")


EXECUTION_ERROR_PROMPT = Template("""Attempt $attempt/$max_attempts to fix the following SymPy ODE code.

The code was generated by an LLM that was given this task:
\"\"\"
You will receive a list of equations extracted from a scientific paper.
Each equation is represented as a tuple: (equation_string, equation_language), separated by newlines.

Select the correct text tuple(s) and transform the equations into a sympy representation.
- IGNORE equations that are simple definitions, error functions, or single variable definitions without derivatives.
- Instead of using unicode characters, spell out symbols in lowercase (e.g., theta, omega).
- If presented with two possible systems, choose the simplified/reduced one with fewer terms.
\"\"\"

The generated code failed with the following error:
ERROR: $error

CODE TO FIX:
$ode_str

Your task: Fix ONLY what is causing the error above. Do not restructure or rewrite the code unnecessarily.

Return ONLY a working Python code snippet with:
- import sympy
- t = sympy.symbols("t")
- State variables as Functions: S = sympy.Function("S")
- Parameters as symbols: beta = sympy.symbols("beta")
- Python reserved keywords renamed with a trailing underscore (e.g., lambda_ instead of lambda)
- odes = [sympy.Eq(...), ...]
""")


ODE_PDF_PROMPT = """Scan through this PDF document to find all systems of ordinary differential equations (ODEs). There should be a singular 
page that contains the system of equations.

For each ODE system found, transform the equations into a sympy representation following this exact style:
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

Look for differential equations with dX/dt notation or similar
Instead of using unicode characters, spell out in symbols in lowercase like theta, omega, etc.
There can exist multiple equation systems exist in the PDF, use your best judgement to identify the system of equations that define the model
Provide only the code snippets with no explanation
"""

ODE_MARKDOWN_PROMPT = """You will receive a list of equations extracted from a scientific paper.
Each equation is represented as a tuple: (equation_string, equation_language), separated by newlines.

The ODE system will either be contained in a single tuple or spread across multiple *adjacent*
consecutive tuples. Do not combine non-adjacent tuples.

Transform the selected equations into a SymPy representation following this exact style:

import sympy

t = sympy.symbols("t")

S, E, I, R = sympy.symbols("S E I R", cls=sympy.Function)

b, g, r = sympy.symbols("b g r")

odes = [
    sympy.Eq(S(t).diff(t), -b * S(t) * I(t)),
    sympy.Eq(E(t).diff(t), b * S(t) * I(t) - r * E(t)),
    sympy.Eq(I(t).diff(t), r * E(t) - g * I(t)),
    sympy.Eq(R(t).diff(t), g * I(t))
]

IGNORE equations that are:
- Simple definitions or substitutions (e.g., Q → C, N = S + I + R)
- Error/loss/objective functions (e.g., err = ||C - Ĉ||₂)
- Normalisation constraints (e.g., S + E + I + R = N)
- Integral or cumulative forms (e.g., C(t) = ∫ I(τ)dτ)
- Discrete-time recurrences (e.g., I_{n+1} = ...)
- Single variable definitions without derivatives

If multiple candidate ODE systems exist, prefer the self-contained one where every
RHS symbol is defined within the system, with fewer state variables.

Symbol naming rules:
- Never use Greek or other unicode characters directly
- Spell out Greek letters in lowercase: beta, gamma, mu, theta, omega, etc.
- Subscripts become suffixes: β₁ → beta1, γ_eff → gamma_eff
- Use short alphanumeric names only

Output rules:
- Begin with `import sympy` and nothing else before it
- Output raw Python only — no markdown fences, no explanation, no preamble
- If no valid ODE system is found, output only: odes = []
"""


ODE_MULTIPLE_IMAGE_PROMPT = """You will be given a series of images representing equations from a paper.
The ODE system will either be contained in a single image or spread across multiple *adjacent*
consecutive images in the order provided. Do not combine equations from non-adjacent images.

Transform the selected equations into a SymPy representation following this exact style:

import sympy

t = sympy.symbols("t")

S, E, I, R = sympy.symbols("S E I R", cls=sympy.Function)

b, g, r = sympy.symbols("b g r")

odes = [
    sympy.Eq(S(t).diff(t), -b * S(t) * I(t)),
    sympy.Eq(E(t).diff(t), b * S(t) * I(t) - r * E(t)),
    sympy.Eq(I(t).diff(t), r * E(t) - g * I(t)),
    sympy.Eq(R(t).diff(t), g * I(t))
]

IGNORE equations that are:
- Simple definitions or substitutions (e.g., Q → C, N = S + I + R)
- Error/loss/objective functions (e.g., err = ||C - Ĉ||₂)
- Normalisation constraints (e.g., S + E + I + R = N)
- Integral or cumulative forms (e.g., C(t) = ∫ I(τ)dτ)
- Discrete-time recurrences (e.g., I_{n+1} = ...)
- Single variable definitions without derivatives
- Equations that appear truncated or partially visible in the image

If multiple candidate ODE systems exist, prefer the self-contained one where every
RHS symbol is defined within the system, with fewer state variables.

Symbol naming rules:
- Never use Greek or other unicode characters directly
- Spell out Greek letters in lowercase: beta, gamma, mu, theta, omega, etc.
- Subscripts become suffixes: β₁ → beta1, γ_eff → gamma_eff
- If a symbol is ambiguous due to image quality, choose the most epidemiologically
  conventional interpretation (e.g., prefer `mu` over `u` for a Greek-looking character)
- Use short alphanumeric names only

Output rules:
- Begin with `import sympy` and nothing else before it
- Output raw Python only — no markdown fences, no explanation, no preamble
- If no valid ODE system is found, output only: odes = []
"""

TABLE_SELECTION_PROMPT = Template("""
You are screening the tables of an epidemiological modeling paper. For each
table you are given only its caption, column header row(s) and footer
(footnotes), not its body.

$model_context
Mark a table as relevant if it likely reports values of the model's INPUT
parameters (transmission/recovery/progression rates, probabilities,
durations, R0, population sizes, initial conditions, priors), including
tables that give different values per scenario (country, intervention,
variant, time period, age group).

Tables that are NOT relevant, even if they are full of numbers:
- model outputs: projections, peak sizes, cumulative cases or deaths, cases
  averted, costs, final sizes
- observed data: case counts, time series, demographics, study populations
- sensitivity indices (PRCC, Sobol, elasticities) and model-fit statistics
- glossaries that list symbols and meanings but no values

Return one entry per table, using each table_id exactly as given.

Tables:
$tables
""")


SCENARIO_EXTRACTION_PROMPT = Template("""
You are extracting the parameterization of an epidemiological model from the
tables of the paper that describes it.
$table_format

$model_context
Organize the values into scenarios:
- A scenario is one complete parameterization of the model, e.g. the fit for
  one country, one intervention setting, one variant or one time period.
- Put values that hold in every scenario in `shared_parameters`, and only the
  values that differ in each scenario's `parameters`.
- If the paper has a single parameterization, put every value in
  `shared_parameters` and return an empty `scenarios` list.
- Use the same `name` for the same parameter across scenarios and tables.

Rules for each value:
- Only extract model INPUT parameters. Skip rows that are model outputs,
  observed data, or headers/sub-headings.
- Naming: `display_name` is the parameter's symbol with Greek letters as
  Unicode characters ('\\beta', 'beta' or MathML <mi>β</mi> -> 'β';
  'gamma_1' -> 'γ_1'). `name` is that symbol spelled out in ASCII
  ('β' -> 'beta', 'γ_1' -> 'gamma_1', 'Λ' -> 'Lambda'). Build
  `name` from the symbol, never from the description.
- Values: if the cell gives a number, put it in `value` (write '2.1 x 10^-3'
  as 0.0021; '45%' -> 0.45 only if the parameter is a proportion or
  probability, otherwise keep 45 and note the unit). If the cell gives an
  expression such as '1/(70*360)' or '1/5.2', put it in `value_expression`
  exactly as written, in sympy syntax, and leave `value` null. Never
  evaluate or simplify an expression.
- Uncertainty: when a cell also gives a fitted/prior/plausible range, a CI,
  or a mean with SD/SE, record it in `uncertainty` in addition to `value`
  ('0.3 (0.2-0.4)' -> value 0.3, range or CI 0.2 to 0.4; '5.2 ± 1.1' ->
  value 5.2, standard_deviation 1.1). If the cell has a range but no point
  estimate, leave `value` null and fill `uncertainty`. Only fill
  `distribution` when a distribution family is named ('Gamma(2, 3)').
- Units: use the unit column, the row label, the caption or the footnotes.
  Write them as a sympy expression ('1/day', 'day', 'person'). Do not guess
  units that are not stated or clearly implied.
- `description`: what the parameter means, taken from the table's
  description/definition column if it has one, otherwise from the row
  label, caption or footnotes. Fill it for every parameter you can.
- Resolve footnote markers against the footnotes and drop them from names
  and values.
- Copy the value cell's text into `verbatim` and record its `table_id`.
- Do not invent parameters that are not in the tables.

Tables:
$tables
""")

JATS_TABLE_FORMAT = """
Each table is given as TSV after a '=== table_id' line. Lines starting with
'#' are the table caption and footnotes; they often carry the units, the
location or the model variant, so read them. Cells, caption and footnotes
keep their original JATS XML markup: <sup>, <sub>, <italic>, MathML or
<tex-math>; read the math, not the markup. Footnote markers are <xref>
elements (often inside <sup>) pointing at the footnote with that <label>.
"""


_MODEL_INTRO = """
The paper's model has already been extracted from its equations. Its
parameters are listed below with the transitions (from -> to, and the rate
law) each one appears in."""


MODEL_SUMMARY_TEMPLATE = Template(_MODEL_INTRO + """ Tables providing values or descriptions for
these are relevant.

$parameters
""")


MODEL_CONTEXT_TEMPLATE = Template(_MODEL_INTRO + """

For every table row, set `model_parameter` to the model parameter that is
the same quantity, or null if none is. The model's names were chosen
independently of the tables and often differ from the table's symbols (the
table's 'k' may be the model's 'kappa', 'ω′' may be 'omega1', 'γ_a' may be
'gamma2'). So match on what the parameter does: compare the row's
description and symbol with the transitions the model parameter controls
(e.g. a 'rate of progression from exposed to asymptomatic' belongs to the
parameter in the E -> A rate law). Map each model parameter to at most one
row per scenario.

$parameters
""")
