
# Comparison by Subtraction
## Model: BIOMD0000000962
### Timestamp: 2025-09-08_12-22-53

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(C(t), t), (gamma2 + sigma*(1 - gamma2))*Q(t))`
- Extracted: `Eq(Derivative(C(t), t), (gamma2 + sigma*(1 - gamma2))*Q(t))`
- Difference: `0`

**Equation 1:**
- Correct:   `Eq(Derivative(Q(t), t), gamma1*U(t) - (gamma2 + sigma*(1 - gamma2))*Q(t))`
- Extracted: `Eq(Derivative(Q(t), t), gamma1*U(t) - (gamma2 + sigma*(1 - gamma2))*Q(t))`
- Difference: `0`

**Equation 2:**
- Correct:   `Eq(Derivative(S(t), t), -a*S(t)*U(t)/N)`
- Extracted: `Eq(Derivative(S(t), t), -alpha*S(t)*U(t)/N)`
- Difference: `(a - alpha)*S(t)*U(t)/N`

**Equation 3:**
- Correct:   `Eq(Derivative(U(t), t), -gamma1*U(t) + a*S(t)*U(t)/N)`
- Extracted: `Eq(Derivative(U(t), t), -gamma1*U(t) + alpha*S(t)*U(t)/N)`
- Difference: `(-a + alpha)*S(t)*U(t)/N`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(C(t), t), (gamma2 + sigma*(1 - gamma2))*Q(t))`
- Corrected: `Eq(Derivative(C(t), t), (gamma2 + sigma*(1 - gamma2))*Q(t))`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(Q(t), t), gamma1*U(t) - (gamma2 + sigma*(1 - gamma2))*Q(t))`
- Corrected: `Eq(Derivative(Q(t), t), gamma1*U(t) - (gamma2 + sigma*(1 - gamma2))*Q(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(S(t), t), -a*S(t)*U(t)/N)`
- Corrected: `Eq(Derivative(S(t), t), -alpha*S(t)*U(t)/N)`
- Difference: `(a - alpha)*S(t)*U(t)/N`

**Equation 3:**
- Correct: `Eq(Derivative(U(t), t), -gamma1*U(t) + a*S(t)*U(t)/N)`
- Corrected: `Eq(Derivative(U(t), t), -gamma1*U(t) + alpha*S(t)*U(t)/N)`
- Difference: `(-a + alpha)*S(t)*U(t)/N`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(C(t), t), (gamma2 + sigma*(1 - gamma2))*Q(t))`
- Matrix:  `Eq(Derivative(C(t), t), Q*(gamma2 + sigma*(1 - gamma2)))`
- Difference: `(-Q + Q(t))*(gamma2 - sigma*(gamma2 - 1))`

**Equation 1:**
- Correct: `Eq(Derivative(Q(t), t), gamma1*U(t) - (gamma2 + sigma*(1 - gamma2))*Q(t))`
- Matrix:  `Eq(Derivative(Q(t), t), -Q*(gamma2 + sigma*(1 - gamma2)) + U*gamma1)`
- Difference: `Q*(gamma2 - sigma*(gamma2 - 1)) - U*gamma1 + gamma1*U(t) - (gamma2 - sigma*(gamma2 - 1))*Q(t)`

**Equation 2:**
- Correct: `Eq(Derivative(S(t), t), -a*S(t)*U(t)/N)`
- Matrix:  `Eq(Derivative(S(t), t), -U*alpha*S(t)/N)`
- Difference: `(U*alpha - a*U(t))*S(t)/N`

**Equation 3:**
- Correct: `Eq(Derivative(U(t), t), -gamma1*U(t) + a*S(t)*U(t)/N)`
- Matrix:  `Eq(Derivative(U(t), t), -U*gamma1 + U*alpha*S(t)/N)`
- Difference: `(N*gamma1*(U - U(t)) - U*alpha*S(t) + a*S(t)*U(t))/N`

