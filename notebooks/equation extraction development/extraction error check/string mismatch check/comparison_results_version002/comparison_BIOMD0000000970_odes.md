
# Comparison by Subtraction
## Model: BIOMD0000000970
### Timestamp: 2025-09-08_13-03-45

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(E(t), t), -alpha*E(t) + beta*r_1*I(t)*S(t)/N + beta_2*r_2*E(t)*S(t)/N)`
- Extracted: `Eq(Derivative(E(t), t), -alpha*E(t) + beta1*r1*I(t)*S(t)/N + beta2*r2*E(t)*S(t)/N)`
- Difference: `(-beta*r_1*I(t) + beta1*r1*I(t) + beta2*r2*E(t) - beta_2*r_2*E(t))*S(t)/N`

**Equation 1:**
- Correct:   `Eq(Derivative(I(t), t), alpha*E(t) - gamma*I(t))`
- Extracted: `Eq(Derivative(I(t), t), alpha*E(t) - gamma*I(t))`
- Difference: `0`

**Equation 2:**
- Correct:   `Eq(Derivative(R(t), t), gamma*I(t))`
- Extracted: `Eq(Derivative(R(t), t), gamma*I(t))`
- Difference: `0`

**Equation 3:**
- Correct:   `Eq(Derivative(S(t), t), -beta_1*r_1*I(t)*S(t)/N - beta_2*r_2*E(t)*S(t)/N)`
- Extracted: `Eq(Derivative(S(t), t), -beta1*r1*I(t)*S(t)/N - beta2*r2*E(t)*S(t)/N)`
- Difference: `(-beta1*r1*I(t) - beta2*r2*E(t) + beta_1*r_1*I(t) + beta_2*r_2*E(t))*S(t)/N`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(E(t), t), -alpha*E(t) + beta*r_1*I(t)*S(t)/N + beta_2*r_2*E(t)*S(t)/N)`
- Corrected: `Eq(Derivative(E(t), t), -alpha*E(t) + beta1*r1*I(t)*S(t)/N + beta2*r2*E(t)*S(t)/N)`
- Difference: `(-beta*r_1*I(t) + beta1*r1*I(t) + beta2*r2*E(t) - beta_2*r_2*E(t))*S(t)/N`

**Equation 1:**
- Correct: `Eq(Derivative(I(t), t), alpha*E(t) - gamma*I(t))`
- Corrected: `Eq(Derivative(I(t), t), alpha*E(t) - gamma*I(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(R(t), t), gamma*I(t))`
- Corrected: `Eq(Derivative(R(t), t), gamma*I(t))`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(S(t), t), -beta_1*r_1*I(t)*S(t)/N - beta_2*r_2*E(t)*S(t)/N)`
- Corrected: `Eq(Derivative(S(t), t), -beta1*r1*I(t)*S(t)/N - beta2*r2*E(t)*S(t)/N)`
- Difference: `(-beta1*r1*I(t) - beta2*r2*E(t) + beta_1*r_1*I(t) + beta_2*r_2*E(t))*S(t)/N`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(E(t), t), -alpha*E(t) + beta*r_1*I(t)*S(t)/N + beta_2*r_2*E(t)*S(t)/N)`
- Matrix:  `Eq(Derivative(E(t), t), -alpha*E(t) + beta1*r1*I(t)*S(t)/N + beta2*r2*E(t)*S(t)/N)`
- Difference: `(beta*r_1*I(t) - beta1*r1*I(t) - beta2*r2*E(t) + beta_2*r_2*E(t))*S(t)/N`

**Equation 1:**
- Correct: `Eq(Derivative(I(t), t), alpha*E(t) - gamma*I(t))`
- Matrix:  `Eq(Derivative(I(t), t), alpha*E(t) - gamma*I(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(R(t), t), gamma*I(t))`
- Matrix:  `Eq(Derivative(R(t), t), gamma*I(t))`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(S(t), t), -beta_1*r_1*I(t)*S(t)/N - beta_2*r_2*E(t)*S(t)/N)`
- Matrix:  `Eq(Derivative(S(t), t), -beta1*r1*I(t)*S(t)/N - beta2*r2*E(t)*S(t)/N)`
- Difference: `(beta1*r1*I(t) + beta2*r2*E(t) - beta_1*r_1*I(t) - beta_2*r_2*E(t))*S(t)/N`

