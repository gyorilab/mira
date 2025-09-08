
# Comparison by Subtraction
## Model: BIOMD0000000979
### Timestamp: 2025-09-08_14-30-09

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(E(t), t), -sigma*E(t) + I(t)*S(t)*beta(t)/N)`
- Extracted: `Eq(Derivative(E(t), t), -sigma*E(t) + beta*I(t)*S(t)/N)`
- Difference: `(beta - beta(t))*I(t)*S(t)/N`

**Equation 1:**
- Correct:   `Eq(Derivative(I(t), t), -gamma*I(t) + sigma*E(t))`
- Extracted: `Eq(Derivative(I(t), t), -gamma*I(t) + sigma*E(t))`
- Difference: `0`

**Equation 2:**
- Correct:   `Eq(Derivative(R(t), t), gamma*I(t) - omega*R(t))`
- Extracted: `Eq(Derivative(R(t), t), gamma*I(t) - omega*R(t))`
- Difference: `0`

**Equation 3:**
- Correct:   `Eq(Derivative(S(t), t), omega*R(t) - I(t)*S(t)*beta(t)/N)`
- Extracted: `Eq(Derivative(S(t), t), omega*R(t) - beta*I(t)*S(t)/N)`
- Difference: `(-beta + beta(t))*I(t)*S(t)/N`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(E(t), t), -sigma*E(t) + I(t)*S(t)*beta(t)/N)`
- Corrected: `Eq(Derivative(E(t), t), -sigma*E(t) + beta*I(t)*S(t)/N)`
- Difference: `(beta - beta(t))*I(t)*S(t)/N`

**Equation 1:**
- Correct: `Eq(Derivative(I(t), t), -gamma*I(t) + sigma*E(t))`
- Corrected: `Eq(Derivative(I(t), t), -gamma*I(t) + sigma*E(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(R(t), t), gamma*I(t) - omega*R(t))`
- Corrected: `Eq(Derivative(R(t), t), gamma*I(t) - omega*R(t))`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(S(t), t), omega*R(t) - I(t)*S(t)*beta(t)/N)`
- Corrected: `Eq(Derivative(S(t), t), omega*R(t) - beta*I(t)*S(t)/N)`
- Difference: `(-beta + beta(t))*I(t)*S(t)/N`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(E(t), t), -sigma*E(t) + I(t)*S(t)*beta(t)/N)`
- Matrix:  `Eq(Derivative(E(t), t), -sigma*E(t) + beta*I(t)*S(t)/N)`
- Difference: `(-beta + beta(t))*I(t)*S(t)/N`

**Equation 1:**
- Correct: `Eq(Derivative(I(t), t), -gamma*I(t) + sigma*E(t))`
- Matrix:  `Eq(Derivative(I(t), t), -gamma*I(t) + sigma*E(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(R(t), t), gamma*I(t) - omega*R(t))`
- Matrix:  `Eq(Derivative(R(t), t), gamma*I(t) - omega*R(t))`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(S(t), t), omega*R(t) - I(t)*S(t)*beta(t)/N)`
- Matrix:  `Eq(Derivative(S(t), t), omega*R(t) - beta*I(t)*S(t)/N)`
- Difference: `(beta - beta(t))*I(t)*S(t)/N`

