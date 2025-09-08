from string import Template


ODE_IMAGE_PROMPT = """Transform these equations into a sympy representation based on the example style below

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


Rules for accurate extraction:

1. **POPULATION CONSERVATION**
   - Outflows from one compartment must equal inflows to others
   - Check symmetry: terms leaving S should enter E/I

2. **TRANSMISSION STRUCTURE**
   - Transmission terms involve products of compartments (example: S*I)
   - Usually normalized by population (check for /N)
   - Appear negative in source, positive in destination

3. **PROGRESSION PATTERNS**
   - Disease stages flow sequentially (S→E→I→R)
   - Exit rates are proportional to compartment size
   - When paths split, proportions should sum appropriately

4. **MATHEMATICAL STRUCTURE**
   - Multiple terms affecting one compartment: usually added (+)
   - Independent processes: addition
   - Check operator precedence and grouping carefully

5. **PARAMETER CONSISTENCY**
   - Same biological process = same parameter symbol
   - Rates are positive
   - Similar compartments have similar equation structures

6. **COMPLETENESS CHECKS**
   - Every compartment mentioned should have an equation
   - Every parameter shown should be used consistently
   - All pathways visible should appear in equations

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

CRITICAL: Preserve ALL content between iterations. Only fix clear errors that prevent execution or change mathematical meaning.

Follow these steps for checking and correcting errors:

1. EXECUTION ERRORS:
- Check missing imports, undefined variables, syntax errors
- Required imports: Symbol, Function, Eq, Derivative from sympy
- Check for namespace conflicts (avoid mixing 'import sympy' with 'from sympy import *')
- Verify all used functions are imported (exp, log, sin, cos, etc.)

**If you find undefined variables:**
- First check if it's a typo of an existing variable
- If not a typo, determine from context if it should be:
  - A Symbol (constant parameter)
  - A Function (time-varying state variable)
- Add the definition BEFORE its first use
- Make sure that all variables are defined and the number of equations match

2. PARAMETER CONSISTENCY:
- Every parameter in equations must be defined
- Parameter definition rules:

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

CRITICAL: FUNCTION DEFINITION FOR ODEs
- Any variable appearing in a differential equation's left-hand side MUST be a Function, not a Symbol!
- You MUST define every time-varying variable as: S = sympy.Function("S")
- NEVER use any other form, examples for WRONG use: S = sympy.Function("S")(t) or sympy.Functions("S")
- Use ONLY sympy.Function, never any variant
- In equations, always use S(t), e.g.: sympy.Eq(S(t).diff(t), ...)

3. TIME DEPENDENCY:
- If X appears in Derivative(X(t), t), X(t).diff(t), or on LHS dX/dt → X must be Function('X'); use X(t) in the equations
- When converting Symbol→Function, update all occurrences in equations and initial conditions (use X(0))

TIME-VARYING COMPARTMENT RULE:
- Any variable appearing with d/dt (Derivative or .diff) on the left side of an equation must be defined as a sympy.Function, not a Symbol.
- For each such variable X:
  1) Define as X = sympy.Function("X") (preserve exact name and subscripts).
  2) Use X(t) everywhere in equations and initial conditions.
- The number of state equations must match the number of distinct time-varying Functions.

CRITICAL ERROR PATTERN TO CHECK:
- If you see "TypeError: 'Symbol' object is not callable" or any usage like X(t):
  - That variable MUST be defined as Function('X'), not Symbol('X')
  - Search for all occurrences of X(t) in the code
  - For EACH variable found with (t), change its definition to Function

4. MATHEMATICAL VALIDATION:
- Verify internal consistency: each term appearing on one side of an equation should have corresponding balance elsewhere in the system
- Validate mathematical plausibility: ensure terms make dimensional sense (rates multiply compartments, not other rates) and follow conservation principles
- Verify equation completeness: each compartment mentioned should have both inflow and outflow terms somewhere in the system
- Don't drop terms even if they seem small
*CRITICAL*: - Verify that every variable (S, E, I, R, H, etc.) that appears anywhere in the equations has its own differential equation in the system - if H(t) appears in any equation, there MUST be a dH/dt equation.


*CRITICAL ARITHMETIC OPERATION CHECKS:*
- Verify correct use of + (addition) vs * (multiplication)
- Check that terms are properly separated by + or - operators
- Ensure parentheses are correctly placed around grouped terms
- Watch for incorrect multiplication where addition should be used
- Check coefficient consistency: the same parameter should have consistent usage across all equations
- If N appears anywhere (defined or referenced), verify that contact terms include /N exactly where shown in the pattern; missing /N is an error


5. CONCEPT GROUNDING:
- Every Symbol/Function in code should have a matching concept entry
- Concept names must match variable names exactly
- **Variable type must match usage**: If X appears in Derivative(X(t), t), X must be Function not Symbol
- **Preserve parameter distinctness**: If concepts show as different compartments, they need different parameters

CONCEPT PRESERVATION RULES:
- Return the EXACT SAME concept_data dictionary if no concept errors found
- NEVER return empty {{}} unless input was also empty
- Only modify concepts if there are actual concept_errors to fix
- For "corrected_concepts": ALWAYS return a dictionary object, NEVER a string

Output Format (must be valid JSON):
{{
    "has_errors": true|false,
    "errors": {{
        "execution_errors": [...],
        "parameter_errors": [...],
        "time_dependency_errors": [...],
        "concept_errors": [...]
    }},
    "auto_fixes_applied": [...],
    "corrected_code": "# complete fixed SymPy code with all imports and odes definition",
    "corrected_concepts": {{...}},
    "confidence": "high/medium/low",
    "manual_review_needed": [...]
}}
RULES:
- Keep ALL original structure, naming, and formatting
- Do NOT standardize notation
- Do NOT change parameter names or variable names
- Do NOT add unnecessary attributes or constraints
- Preserve the exact mathematical structure from the original
- Preserve ALL subscripts exactly as shown (e.g., keep rho_1, gamma_r, beta_prime; do not rename or normalize)

- Return ONLY valid JSON!
- The corrected_code must define the variable called `odes`
- Include all necessary imports in corrected_code
- If no changes needed, return has_errors: false with original code
"""