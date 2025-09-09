## MULTI-AGENT ARCHITECTURE

for each agent, different: 
- role assignment
- instructions (prompt)
    - output format
- tools

need to put these somewhere:

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

### CREW
linear workflow 

### 0. Initial extraction

**Role assignment:**

**Instructions:**

Output format:

**Tools:**

### 1. Extraction evaluation

**Role assignment:**

**Instructions:**

EXECUTION ERRORS:

- Check missing imports, undefined variables, syntax errors
- Required imports: Symbol, Function, Eq, Derivative from sympy
- Check for namespace conflicts (avoid mixing 'import sympy' with 'from sympy import *')
- Verify all used functions are imported (exp, log, sin, cos, etc.)

If you find undefined variables:

- First check if it's a typo of an existing variable
- If not a typo, determine from context if it should be:
  - A Symbol (constant parameter)
  - A Function (time-varying state variable)
- Add the definition BEFORE its first use
- Make sure that all variables are defined and the number of equations match

Output format:

**Tools:**


### 2. Parameter consistency check

**Role assignment:**

**Instructions:**

PARAMETER CONSISTENCY:

- Every parameter in equations must be defined
- Parameter definition rules:

Use Symbol for:

- Rate constants (beta, gamma, mu, alpha, etc.)
- Fixed parameters (N, K, R0, etc.)
- Initial conditions when defined as constants
- Definition: `beta = Symbol('beta', positive=True, real=True)`

Use Function for:

- ANY variable that appears with d/dt in equations
- State variables (S, I, R, x, y, etc.)
- Time-varying quantities
- Definition: `S = Function('S')` then use as `S(t)` in equations

CRITICAL: FUNCTION DEFINITION FOR ODEs

- Any variable appearing in a differential equation's left-hand side MUST be a Function, not a Symbol!
- You MUST define every time-varying variable as: S = sympy.Function("S")
- NEVER use any other form, examples for WRONG use: S = sympy.Function("S")(t) or sympy.Functions("S")
- Use ONLY sympy.Function, never any variant
- In equations, always use S(t), e.g.: sympy.Eq(S(t).diff(t), …)
- Parameters/scalars (e.g., n, beta, sigma, theta, kappa, gamma_*, rho_*, etc.) must be Symbols, not Functions

Output format:

**Tools:**

### 3. Time-dependency check

**Role assignment:**

**Instructions:**

TIME DEPENDENCY:

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
- Treat as an error if any n parameter appears as n(t) without evidence of time dependence

Output format:

**Tools:**

### 4. Mathematical validation

**Role assignment:**

**Instructions:**

- Verify internal consistency: each term appearing on one side of an equation should have corresponding balance elsewhere in the system- Validate mathematical plausibility: ensure terms make dimensional sense (rates multiply compartments, not other rates) and follow conservation principles
- Verify equation completeness: each compartment mentioned should have both inflow and outflow terms somewhere in the system
- Don't drop terms even if they seem small
- Verify that every variable (S, E, I, R, H, etc.) that appears anywhere in the equations has its own differential equation in the system - if H(t) appears in any equation, there MUST be a dH/dt equation.

ARITHMETIC OPERATION CHECKS:
- Verify correct use of + (addition) vs * (multiplication)
- Check that terms are properly separated by + or - operators
- Ensure parentheses are correctly placed around grouped terms
- Watch for incorrect multiplication where addition should be used
- Check coefficient consistency: the same parameter should have consistent usage across all equations
- The order of terms and factors in all mathematical expressions MUST be preserved exactly as in the original, never reorder, regroup, or rearrange any terms, factors, or operands in sums, products, or other operations.
- If N appears anywhere (defined or referenced), verify that contact terms include /N exactly where shown in the pattern; missing /N is an error

Output format:

**Tools:**

### 5. Concept grounding check

**Role assignment:**

**Instructions:**

- Every Symbol/Function in code should have a matching concept entry
- Concept names must match variable names exactly
- Variable type must match usage: If X appears in Derivative(X(t), t), X must be Function not Symbol
- Preserve parameter distinctness: If concepts show as different compartments, they need different parameters

CONCEPT PRESERVATION RULES:

- Return the EXACT SAME concept_data dictionary if no concept errors found
- NEVER return empty {{}} unless input was also empty
- Only modify concepts if there are actual concept_errors to fix
- For "corrected_concepts": ALWAYS return a dictionary object, NEVER a string

Output format:

**Tools:**

### 6. Quantitative evaluation of the extraction process

**Role assignment:**

**Instructions:**

Output format:

**Tools:**
