
# Comparison by Subtraction
## Model: BIOMD0000000956
### Timestamp: 2025-09-08_11-58-10

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(E(t), t), -alpha*E(t) + beta*I(t)*S(t)/N)`
- Extracted: `Eq(Derivative(E(t), t), -a*E(t) + beta*I(t)*S(t)/N)`
- Difference: `(-a + alpha)*E(t)`

**Equation 1:**
- Correct:   `Eq(Derivative(I(t), t), alpha*E(t) - gamma*I(t))`
- Extracted: `Eq(Derivative(I(t), t), a*E(t) - gamma*I(t))`
- Difference: `(a - alpha)*E(t)`

**Equation 2:**
- Correct:   `Eq(Derivative(R(t), t), gamma*I(t))`
- Extracted: `Eq(Derivative(R(t), t), gamma*I(t))`
- Difference: `0`

**Equation 3:**
- Correct:   `Eq(Derivative(S(t), t), -beta*I(t)*S(t)/N)`
- Extracted: `Eq(Derivative(S(t), t), -beta*I(t)*S(t)/N)`
- Difference: `0`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(E(t), t), -alpha*E(t) + beta*I(t)*S(t)/N)`
- Corrected: `Eq(Derivative(E(t), t), -a*E(t) + beta*I(t)*S(t)/N)`
- Difference: `(-a + alpha)*E(t)`

**Equation 1:**
- Correct: `Eq(Derivative(I(t), t), alpha*E(t) - gamma*I(t))`
- Corrected: `Eq(Derivative(I(t), t), a*E(t) - gamma*I(t))`
- Difference: `(a - alpha)*E(t)`

**Equation 2:**
- Correct: `Eq(Derivative(R(t), t), gamma*I(t))`
- Corrected: `Eq(Derivative(R(t), t), gamma*I(t))`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(S(t), t), -beta*I(t)*S(t)/N)`
- Corrected: `Eq(Derivative(S(t), t), -beta*I(t)*S(t)/N)`
- Difference: `0`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(E(t), t), -alpha*E(t) + beta*I(t)*S(t)/N)`
- Matrix:  `Eq(Derivative(E(t), t), -a*E(t) + beta*I(t)*S(t)/N)`
- Difference: `(a - alpha)*E(t)`

**Equation 1:**
- Correct: `Eq(Derivative(I(t), t), alpha*E(t) - gamma*I(t))`
- Matrix:  `Eq(Derivative(I(t), t), a*E(t) - gamma*I(t))`
- Difference: `(-a + alpha)*E(t)`

**Equation 2:**
- Correct: `Eq(Derivative(R(t), t), gamma*I(t))`
- Matrix:  `Eq(Derivative(R(t), t), gamma*I(t))`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(S(t), t), -beta*I(t)*S(t)/N)`
- Matrix:  `Eq(Derivative(S(t), t), -beta*I(t)*S(t)/N)`
- Difference: `0`

