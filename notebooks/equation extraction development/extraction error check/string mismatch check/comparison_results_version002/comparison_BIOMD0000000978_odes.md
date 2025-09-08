
# Comparison by Subtraction
## Model: BIOMD0000000978
### Timestamp: 2025-09-08_14-16-57

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(E(t), t), -sigma*E(t) + beta*(1 - epsilon)*I(t)*S(t)/N)`
- Extracted: `Eq(Derivative(E(t), t), -sigma*E(t) + beta*(1 - epsilon)*I(t)*S(t)/N)`
- Difference: `0`

**Equation 1:**
- Correct:   `Eq(Derivative(I(t), t), -gamma*I(t) + sigma*E(t))`
- Extracted: `Eq(Derivative(I(t), t), -gamma*I(t) + sigma*E(t))`
- Difference: `0`

**Equation 2:**
- Correct:   `Eq(Derivative(R(t), t), gamma*I(t))`
- Extracted: `Eq(Derivative(R(t), t), gamma*I(t))`
- Difference: `0`

**Equation 3:**
- Correct:   `Eq(Derivative(S(t), t), beta*(epsilon - 1)*I(t)*S(t)/N)`
- Extracted: `Eq(Derivative(S(t), t), beta*(epsilon - 1)*I(t)*S(t)/N)`
- Difference: `0`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(E(t), t), -sigma*E(t) + beta*(1 - epsilon)*I(t)*S(t)/N)`
- Corrected: `Eq(Derivative(E(t), t), -sigma*E(t) + beta*(1 - epsilon)*I(t)*S(t)/N)`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(I(t), t), -gamma*I(t) + sigma*E(t))`
- Corrected: `Eq(Derivative(I(t), t), -gamma*I(t) + sigma*E(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(R(t), t), gamma*I(t))`
- Corrected: `Eq(Derivative(R(t), t), gamma*I(t))`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(S(t), t), beta*(epsilon - 1)*I(t)*S(t)/N)`
- Corrected: `Eq(Derivative(S(t), t), beta*(epsilon - 1)*I(t)*S(t)/N)`
- Difference: `0`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(E(t), t), -sigma*E(t) + beta*(1 - epsilon)*I(t)*S(t)/N)`
- Matrix:  `Eq(Derivative(E(t), t), -sigma*E(t) + beta*(1 - epsilon)*I(t)*S(t)/N)`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(I(t), t), -gamma*I(t) + sigma*E(t))`
- Matrix:  `Eq(Derivative(I(t), t), -gamma*I(t) + sigma*E(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(R(t), t), gamma*I(t))`
- Matrix:  `Eq(Derivative(R(t), t), gamma*I(t))`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(S(t), t), beta*(epsilon - 1)*I(t)*S(t)/N)`
- Matrix:  `Eq(Derivative(S(t), t), -beta*(1 - epsilon)*I(t)*S(t)/N)`
- Difference: `0`

