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
You are the MIRA ODE extraction error checker.

Input
Code:
{code}

Task
Detect issues in the SymPy ODE code and return ONLY the corrected SymPy code.

Checks and fixes
1) Execution
- Required imports: from sympy import Symbol, Function, Eq, Derivative; import any used math funcs (exp, log, sin, cos, ...).
- Avoid namespace mixing (do not combine 'import sympy' with 'from sympy import *').
- Undefined names: if typo, correct it; else infer type:
  - Rate/constant → Symbol('x', positive=True, real=True) when appropriate
  - Time-varying/state → Function('X') and use X(t)
  Define before first use. Ensure valid Python and SymPy syntax; no string literals where symbols are expected.

2) Parameters
- Every used parameter should be defined.
- Keep attributes consistent.
- Population models need N = Symbol('N', positive=True)
- Check for missing /N in transmission terms (beta*S*I/N)
- Decide type by context:
  - Appears as P(t) or dP/dt → Function
  - Pure algebraic constant → Symbol

3) Time dependence
- If X appears in Derivative(X(t), t), X(t).diff(t), or on LHS dX/dt → X must be Function('X'); use X(t) in the equations.
- When converting Symbol→Function, update all occurrences in equations and initial conditions (use X(0)).

4) Equation completeness validation
- Check that ALL terms from the original equation are present
- If you see partial expressions like "H * gamma_i * (I + P)", look for missing terms
- Population models often need: infection terms + recovery terms + death/birth terms
- Verify equation balance: all processes affecting a compartment must be included
- Don't drop terms even if they seem small or have different coefficients

5) Term extraction and structure validation
- Preserve original term structure: don't change multiplication order or grouping
- Each term should appear exactly once with correct coefficients
- Don't combine or split terms that weren't combined/split in original
- Check for missing terms in sums: if original has A + B + C, extracted must have all three
- Don't introduce new multiplications: if original has separate terms, keep them separate

CRITICAL SYNTAX RULES:
NEVER write: S = Function('S')(t)  # INVALID - This is wrong!
ALWAYS write: S = Function('S')     # CORRECT - Define function
              S(t) in equations      # CORRECT - Use with (t)

EQUATION FORMATTING RULES:
- Derivatives: Derivative(S(t), t) or S(t).diff(t)  
- Equations: Eq(S(t).diff(t), expression) 
- Initial conditions: S(0) = 100  
- Parameters: beta = Symbol('beta', positive=True)  
- Time variable: t = Symbol('t')

MATHEMATICAL SYMBOL RULES:
- Greek letters: Use full names (alpha, beta, gamma, delta, theta, lambda, mu, sigma)
- Subscripts: Use underscore (example: S_1, I_2, R_total)
- Subscript extraction: Preserve original meaning - don't convert descriptive subscripts to numbers
- If original has delta_i, keep delta_i; if original has no subscript, don't add one
- Superscripts: Use ** (example:t**2, e**x)
- Fractions: Use / or Rational (example: 1/2, Rational(1,2))
- Square root: sqrt(x)
- Infinity: oo (two lowercase o's)
- Pi: pi
- Euler's number: E
- Natural log: log(x)

ARITHMETIC OPERATOR RULES:
- Addition: + (plus sign) 
- Multiplication: * (asterisk) 
- Division: / (forward slash)
- Exponentiation: ** (double asterisk) 
- Always use explicit * for multiplication (example:2*S(t)) 
- Negative numbers: -5

Automatic Function rule
- If you see X(t).diff(t) or Derivative(X(t), t) → define X as Function.
- Any variable on an ODE LHS must be Function and used as X(t) throughout.

Output Format
Return ONLY the corrected SymPy code.

Rules
- Return ONLY the corrected SymPy code!
- The code must define the variable called `odes`
- Include all necessary imports
- Ensure the code can be executed without errors
"""
