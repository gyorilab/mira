
# Comparison by Subtraction
## Model: BIOMD0000000957
### Timestamp: 2025-09-08_12-00-54

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(E(t), t), beta*I(t)*S(t) - epsilon*E(t))`
- Extracted: `Eq(Derivative(E(t), t), beta*I(t)*S(t) - epsilon*E(t))`
- Difference: `0`

**Equation 1:**
- Correct:   `Eq(Derivative(I(t), t), epsilon*E(t) - (mu + rho)*I(t))`
- Extracted: `Eq(Derivative(I(t), t), epsilon*E(t) - (mu + rho)*I(t))`
- Difference: `0`

**Equation 2:**
- Correct:   `Eq(Derivative(R(t), t), -d*R(t) + rho*I(t))`
- Extracted: `Eq(Derivative(R(t), t), -d*R(t) + rho*I(t))`
- Difference: `0`

**Equation 3:**
- Correct:   `Eq(Derivative(S(t), t), -beta*I(t)*S(t))`
- Extracted: `Eq(Derivative(S(t), t), -beta*I(t)*S(t))`
- Difference: `0`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(E(t), t), beta*I(t)*S(t) - epsilon*E(t))`
- Corrected: `Eq(Derivative(E(t), t), beta*I(t)*S(t) - epsilon*E(t))`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(I(t), t), epsilon*E(t) - (mu + rho)*I(t))`
- Corrected: `Eq(Derivative(I(t), t), epsilon*E(t) - (mu + rho)*I(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(R(t), t), -d*R(t) + rho*I(t))`
- Corrected: `Eq(Derivative(R(t), t), -d*R(t) + rho*I(t))`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(S(t), t), -beta*I(t)*S(t))`
- Corrected: `Eq(Derivative(S(t), t), -beta*I(t)*S(t))`
- Difference: `0`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(E(t), t), beta*I(t)*S(t) - epsilon*E(t))`
- Matrix:  `Eq(Derivative(E(t), t), beta*I(t)*S(t) - epsilon*E(t))`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(I(t), t), epsilon*E(t) - (mu + rho)*I(t))`
- Matrix:  `Eq(Derivative(I(t), t), epsilon*E(t) - (mu + rho)*I(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(R(t), t), -d*R(t) + rho*I(t))`
- Matrix:  `Eq(Derivative(R(t), t), -d*R(t) + rho*I(t))`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(S(t), t), -beta*I(t)*S(t))`
- Matrix:  `Eq(Derivative(S(t), t), -beta*I(t)*S(t))`
- Difference: `0`

