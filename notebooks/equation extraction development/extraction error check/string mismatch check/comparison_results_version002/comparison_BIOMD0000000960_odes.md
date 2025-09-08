
# Comparison by Subtraction
## Model: BIOMD0000000960
### Timestamp: 2025-09-08_12-04-35

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(A(t), t), kappa*(1 - rho)*E(t) - mu*A(t))`
- Extracted: `Eq(Derivative(A(t), t), kappa*(1 - rho)*E(t) - mu*A(t))`
- Difference: `0`

**Equation 1:**
- Correct:   `Eq(Derivative(D(t), t), delta_A*mu*A(t) + delta_H*H(t) + delta_I*I(t))`
- Extracted: `Eq(Derivative(D(t), t), delta_A*mu*A(t) + delta_H*H(t) + delta_I*I(t))`
- Difference: `0`

**Equation 2:**
- Correct:   `Eq(Derivative(E(t), t), -kappa*E(t) + beta*(l*H(t) + l_a*A(t) + I(t))*S(t)/N)`
- Extracted: `Eq(Derivative(E(t), t), -kappa*E(t) + beta*(l_H*H(t) + l_a*A(t) + I(t))*S(t)/N)`
- Difference: `beta*(-l + l_H)*H(t)*S(t)/N`

**Equation 3:**
- Correct:   `Eq(Derivative(H(t), t), gamma_a*I(t) - (delta_H + gamma_r)*H(t))`
- Extracted: `Eq(Derivative(H(t), t), gamma_a*I(t) - (delta_H + gamma_r)*H(t))`
- Difference: `0`

**Equation 4:**
- Correct:   `Eq(Derivative(I(t), t), kappa*rho*E(t) - (delta_I + gamma_I + gamma_a)*I(t))`
- Extracted: `Eq(Derivative(I(t), t), kappa*rho*E(t) - (delta_I + gamma_I + gamma_a)*I(t))`
- Difference: `0`

**Equation 5:**
- Correct:   `Eq(Derivative(R(t), t), gamma_I*I(t) + gamma_r*H(t) + mu*(1 - delta_A)*A(t))`
- Extracted: `Eq(Derivative(R(t), t), gamma_I*I(t) + gamma_r*H(t) + mu*(1 - delta_A)*A(t))`
- Difference: `0`

**Equation 6:**
- Correct:   `Eq(Derivative(S(t), t), -beta*(l*H(t) + l_a*A(t) + I(t))*S(t)/N)`
- Extracted: `Eq(Derivative(S(t), t), -beta*(l_H*H(t) + l_a*A(t) + I(t))*S(t)/N)`
- Difference: `beta*(l - l_H)*H(t)*S(t)/N`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(A(t), t), kappa*(1 - rho)*E(t) - mu*A(t))`
- Corrected: `Eq(Derivative(A(t), t), kappa*(1 - rho)*E(t) - mu*A(t))`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(D(t), t), delta_A*mu*A(t) + delta_H*H(t) + delta_I*I(t))`
- Corrected: `Eq(Derivative(D(t), t), delta_A*mu*A(t) + delta_H*H(t) + delta_I*I(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(E(t), t), -kappa*E(t) + beta*(l*H(t) + l_a*A(t) + I(t))*S(t)/N)`
- Corrected: `Eq(Derivative(E(t), t), -kappa*E(t) + beta*(l_H*H(t) + l_a*A(t) + I(t))*S(t)/N)`
- Difference: `beta*(-l + l_H)*H(t)*S(t)/N`

**Equation 3:**
- Correct: `Eq(Derivative(H(t), t), gamma_a*I(t) - (delta_H + gamma_r)*H(t))`
- Corrected: `Eq(Derivative(H(t), t), gamma_a*I(t) - (delta_H + gamma_r)*H(t))`
- Difference: `0`

**Equation 4:**
- Correct: `Eq(Derivative(I(t), t), kappa*rho*E(t) - (delta_I + gamma_I + gamma_a)*I(t))`
- Corrected: `Eq(Derivative(I(t), t), kappa*rho*E(t) - (delta_I + gamma_I + gamma_a)*I(t))`
- Difference: `0`

**Equation 5:**
- Correct: `Eq(Derivative(R(t), t), gamma_I*I(t) + gamma_r*H(t) + mu*(1 - delta_A)*A(t))`
- Corrected: `Eq(Derivative(R(t), t), gamma_I*I(t) + gamma_r*H(t) + mu*(1 - delta_A)*A(t))`
- Difference: `0`

**Equation 6:**
- Correct: `Eq(Derivative(S(t), t), -beta*(l*H(t) + l_a*A(t) + I(t))*S(t)/N)`
- Corrected: `Eq(Derivative(S(t), t), -beta*(l_H*H(t) + l_a*A(t) + I(t))*S(t)/N)`
- Difference: `beta*(l - l_H)*H(t)*S(t)/N`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(A(t), t), kappa*(1 - rho)*E(t) - mu*A(t))`
- Matrix:  `Eq(Derivative(A(t), t), kappa*(1 - rho)*E(t) - mu*A(t))`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(D(t), t), delta_A*mu*A(t) + delta_H*H(t) + delta_I*I(t))`
- Matrix:  `Eq(Derivative(D(t), t), delta_A*mu*A(t) + delta_H*H(t) + delta_I*I(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(E(t), t), -kappa*E(t) + beta*(l*H(t) + l_a*A(t) + I(t))*S(t)/N)`
- Matrix:  `Eq(Derivative(E(t), t), -kappa*rho*E(t) - kappa*(1 - rho)*E(t) + beta*(l_H*H(t) + l_a*A(t) + I(t))*S(t)/N)`
- Difference: `beta*(l - l_H)*H(t)*S(t)/N`

**Equation 3:**
- Correct: `Eq(Derivative(H(t), t), gamma_a*I(t) - (delta_H + gamma_r)*H(t))`
- Matrix:  `Eq(Derivative(H(t), t), gamma_a*I(t) - (delta_H + gamma_r)*H(t))`
- Difference: `0`

**Equation 4:**
- Correct: `Eq(Derivative(I(t), t), kappa*rho*E(t) - (delta_I + gamma_I + gamma_a)*I(t))`
- Matrix:  `Eq(Derivative(I(t), t), kappa*rho*E(t) - (delta_I + gamma_I + gamma_a)*I(t))`
- Difference: `0`

**Equation 5:**
- Correct: `Eq(Derivative(R(t), t), gamma_I*I(t) + gamma_r*H(t) + mu*(1 - delta_A)*A(t))`
- Matrix:  `Eq(Derivative(R(t), t), gamma_I*I(t) + gamma_r*H(t) + mu*(1 - delta_A)*A(t))`
- Difference: `0`

**Equation 6:**
- Correct: `Eq(Derivative(S(t), t), -beta*(l*H(t) + l_a*A(t) + I(t))*S(t)/N)`
- Matrix:  `Eq(Derivative(S(t), t), -beta*(l_H*H(t) + l_a*A(t) + I(t))*S(t)/N)`
- Difference: `beta*(-l + l_H)*H(t)*S(t)/N`

