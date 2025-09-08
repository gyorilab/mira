
# Comparison by Subtraction
## Model: BIOMD0000000974
### Timestamp: 2025-09-08_14-00-27

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(E(t), t), -(epsilon + mu)*E(t) + beta*I(t)*S(t)/N)`
- Extracted: `Eq(Derivative(E(t), t), -(epsilon + mu)*E(t) + beta*I(t)*S(t)/N)`
- Difference: `0`

**Equation 1:**
- Correct:   `Eq(Derivative(I(t), t), epsilon*E(t) - (alpha + gamma + mu)*I(t))`
- Extracted: `Eq(Derivative(I(t), t), epsilon*E(t) - (alpha + gamma + mu)*I(t))`
- Difference: `0`

**Equation 2:**
- Correct:   `Eq(Derivative(R(t), t), gamma*I(t) - mu*R(t))`
- Extracted: `Eq(Derivative(R(t), t), gamma*I(t) - mu*R(t))`
- Difference: `0`

**Equation 3:**
- Correct:   `Eq(Derivative(S(t), t), Lambda - mu*S(t) - beta*I(t)*S(t)/N)`
- Extracted: `Eq(Derivative(S(t), t), lambda_ - mu*S(t) - beta*I(t)*S(t)/N)`
- Difference: `-Lambda + lambda_`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(E(t), t), -(epsilon + mu)*E(t) + beta*I(t)*S(t)/N)`
- Corrected: `Eq(0, -I*S*beta/N - S*mu + lambda_)`
- Difference: `(-I*S*beta + N*(-S*mu + lambda_ + (epsilon + mu)*E(t) + Derivative(E(t), t)) - beta*I(t)*S(t))/N`

**Equation 1:**
- Correct: `Eq(Derivative(I(t), t), epsilon*E(t) - (alpha + gamma + mu)*I(t))`
- Corrected: `Eq(0, -E*(epsilon + mu) + I*S*beta/N)`
- Difference: `(I*S*beta + N*(-E*(epsilon + mu) - epsilon*E(t) + (alpha + gamma + mu)*I(t) + Derivative(I(t), t)))/N`

**Equation 2:**
- Correct: `Eq(Derivative(R(t), t), gamma*I(t) - mu*R(t))`
- Corrected: `Eq(0, E*epsilon - I*(alpha + gamma + mu))`
- Difference: `E*epsilon - I*(alpha + gamma + mu) - gamma*I(t) + mu*R(t) + Derivative(R(t), t)`

**Equation 3:**
- Correct: `Eq(Derivative(S(t), t), Lambda - mu*S(t) - beta*I(t)*S(t)/N)`
- Corrected: `Eq(0, I*gamma - R*mu)`
- Difference: `I*gamma - Lambda - R*mu + mu*S(t) + Derivative(S(t), t) + beta*I(t)*S(t)/N`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(E(t), t), -(epsilon + mu)*E(t) + beta*I(t)*S(t)/N)`
- Matrix:  `Eq(Derivative(E(t), t), -(epsilon + mu)*E(t) + beta*I(t)*S(t)/N)`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(I(t), t), epsilon*E(t) - (alpha + gamma + mu)*I(t))`
- Matrix:  `Eq(Derivative(I(t), t), epsilon*E(t) - (alpha + gamma + mu)*I(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(R(t), t), gamma*I(t) - mu*R(t))`
- Matrix:  `Eq(Derivative(R(t), t), gamma*I(t) - mu*R(t))`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(S(t), t), Lambda - mu*S(t) - beta*I(t)*S(t)/N)`
- Matrix:  `Eq(Derivative(S(t), t), lambda - mu*S(t) - beta*I(t)*S(t)/N)`
- Difference: `Lambda - lambda`

