
# Comparison by Subtraction
## Model: BIOMD0000000958
### Timestamp: 2025-09-08_12-02-24

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(A(t), t), kappa*(-rho1 - rho2 + 1)*E(t))`
- Extracted: `Eq(Derivative(A(t), t), kappa*(-rho_1 - rho_2 + 1)*E(t))`
- Difference: `kappa*(rho1 + rho2 - rho_1 - rho_2)*E(t)`

**Equation 1:**
- Correct:   `Eq(Derivative(E(t), t), -kappa*E(t) + beta*l*H(t)*S(t)/N + beta*I(t)*S(t)/N + beta_prime*P(t)*S(t)/N)`
- Extracted: `Eq(Derivative(E(t), t), -kappa*E(t) + beta*l*H(t)*S(t)/N + beta*I(t)*S(t)/N + beta_prime*P(t)*S(t)/N)`
- Difference: `0`

**Equation 2:**
- Correct:   `Eq(Derivative(F(t), t), delta_h*H(t) + delta_i*I(t) + delta_p*P(t))`
- Extracted: `Eq(Derivative(F(t), t), delta_h*H(t) + delta_i*I(t) + delta_p*P(t))`
- Difference: `0`

**Equation 3:**
- Correct:   `Eq(Derivative(H(t), t), -delta_h*H(t) + gamma_alpha*(I(t) + P(t)) - gamma_r*H(t))`
- Extracted: `Eq(Derivative(H(t), t), -delta_h*H(t) + gamma_a*(I(t) + P(t)) - gamma_r*H(t))`
- Difference: `(gamma_a - gamma_alpha)*(I(t) + P(t))`

**Equation 4:**
- Correct:   `Eq(Derivative(I(t), t), -delta_i*I(t) + kappa*rho1*E(t) - (gamma_alpha + gamma_i)*I(t))`
- Extracted: `Eq(Derivative(I(t), t), -delta*I(t) + kappa*rho_1*E(t) - (gamma_a + gamma_i)*I(t))`
- Difference: `-delta*I(t) + delta_i*I(t) - gamma_a*I(t) + gamma_alpha*I(t) - kappa*rho1*E(t) + kappa*rho_1*E(t)`

**Equation 5:**
- Correct:   `Eq(Derivative(P(t), t), -delta_p*P(t) + kappa*rho2*E(t) - (gamma_alpha + gamma_i)*P(t))`
- Extracted: `Eq(Derivative(P(t), t), -delta_p*P(t) + kappa*rho_2*E(t) - (gamma_a + gamma_i)*P(t))`
- Difference: `-gamma_a*P(t) + gamma_alpha*P(t) - kappa*rho2*E(t) + kappa*rho_2*E(t)`

**Equation 6:**
- Correct:   `Eq(Derivative(R(t), t), gamma_i*(I(t) + P(t)) + gamma_r*H(t))`
- Extracted: `Eq(Derivative(R(t), t), gamma_i*(I(t) + P(t)) + gamma_r*H(t))`
- Difference: `0`

**Equation 7:**
- Correct:   `Eq(Derivative(S(t), t), -beta*l*H(t)*S(t)/N - beta*I(t)*S(t)/N - beta_prime*P(t)*S(t)/N)`
- Extracted: `Eq(Derivative(S(t), t), -beta*l*H(t)*S(t)/N - beta*I(t)*S(t)/N - beta_prime*P(t)*S(t)/N)`
- Difference: `0`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(A(t), t), kappa*(-rho1 - rho2 + 1)*E(t))`
- Corrected: `Eq(Derivative(A(t), t), kappa*(-rho_1 - rho_2 + 1)*E(t))`
- Difference: `kappa*(rho1 + rho2 - rho_1 - rho_2)*E(t)`

**Equation 1:**
- Correct: `Eq(Derivative(E(t), t), -kappa*E(t) + beta*l*H(t)*S(t)/N + beta*I(t)*S(t)/N + beta_prime*P(t)*S(t)/N)`
- Corrected: `Eq(Derivative(E(t), t), -kappa*E(t) + beta*l*H(t)*S(t)/N + beta*I(t)*S(t)/N + beta_prime*P(t)*S(t)/N)`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(F(t), t), delta_h*H(t) + delta_i*I(t) + delta_p*P(t))`
- Corrected: `Eq(Derivative(F(t), t), delta_h*H(t) + delta_i*I(t) + delta_p*P(t))`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(H(t), t), -delta_h*H(t) + gamma_alpha*(I(t) + P(t)) - gamma_r*H(t))`
- Corrected: `Eq(Derivative(H(t), t), -delta_h*H(t) + gamma_a*(I(t) + P(t)) - gamma_r*H(t))`
- Difference: `(gamma_a - gamma_alpha)*(I(t) + P(t))`

**Equation 4:**
- Correct: `Eq(Derivative(I(t), t), -delta_i*I(t) + kappa*rho1*E(t) - (gamma_alpha + gamma_i)*I(t))`
- Corrected: `Eq(Derivative(I(t), t), -delta*I(t) + kappa*rho_1*E(t) - (gamma_a + gamma_i)*I(t))`
- Difference: `-delta*I(t) + delta_i*I(t) - gamma_a*I(t) + gamma_alpha*I(t) - kappa*rho1*E(t) + kappa*rho_1*E(t)`

**Equation 5:**
- Correct: `Eq(Derivative(P(t), t), -delta_p*P(t) + kappa*rho2*E(t) - (gamma_alpha + gamma_i)*P(t))`
- Corrected: `Eq(Derivative(P(t), t), -delta_p*P(t) + kappa*rho_2*E(t) - (gamma_a + gamma_i)*P(t))`
- Difference: `-gamma_a*P(t) + gamma_alpha*P(t) - kappa*rho2*E(t) + kappa*rho_2*E(t)`

**Equation 6:**
- Correct: `Eq(Derivative(R(t), t), gamma_i*(I(t) + P(t)) + gamma_r*H(t))`
- Corrected: `Eq(Derivative(R(t), t), gamma_i*(I(t) + P(t)) + gamma_r*H(t))`
- Difference: `0`

**Equation 7:**
- Correct: `Eq(Derivative(S(t), t), -beta*l*H(t)*S(t)/N - beta*I(t)*S(t)/N - beta_prime*P(t)*S(t)/N)`
- Corrected: `Eq(Derivative(S(t), t), -beta*l*H(t)*S(t)/N - beta*I(t)*S(t)/N - beta_prime*P(t)*S(t)/N)`
- Difference: `0`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(A(t), t), kappa*(-rho1 - rho2 + 1)*E(t))`
- Matrix:  `Eq(Derivative(A(t), t), kappa*(-rho_1 - rho_2 + 1)*E(t))`
- Difference: `kappa*(-rho1 - rho2 + rho_1 + rho_2)*E(t)`

**Equation 1:**
- Correct: `Eq(Derivative(E(t), t), -kappa*E(t) + beta*l*H(t)*S(t)/N + beta*I(t)*S(t)/N + beta_prime*P(t)*S(t)/N)`
- Matrix:  `Eq(Derivative(E(t), t), -kappa*E(t) + beta*l*H(t)*S(t)/N + beta*I(t)*S(t)/N + beta_prime*P(t)*S(t)/N)`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(F(t), t), delta_h*H(t) + delta_i*I(t) + delta_p*P(t))`
- Matrix:  `Eq(Derivative(F(t), t), delta_h*H(t) + delta_i*I(t) + delta_p*P(t))`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(H(t), t), -delta_h*H(t) + gamma_alpha*(I(t) + P(t)) - gamma_r*H(t))`
- Matrix:  `Eq(Derivative(H(t), t), -delta_h*H(t) + gamma_a*(I(t) + P(t)) - gamma_r*H(t))`
- Difference: `(-gamma_a + gamma_alpha)*(I(t) + P(t))`

**Equation 4:**
- Correct: `Eq(Derivative(I(t), t), -delta_i*I(t) + kappa*rho1*E(t) - (gamma_alpha + gamma_i)*I(t))`
- Matrix:  `Eq(Derivative(I(t), t), -delta*I(t) + kappa*rho_1*E(t) - (gamma_a + gamma_i)*I(t))`
- Difference: `delta*I(t) - delta_i*I(t) + gamma_a*I(t) - gamma_alpha*I(t) + kappa*rho1*E(t) - kappa*rho_1*E(t)`

**Equation 5:**
- Correct: `Eq(Derivative(P(t), t), -delta_p*P(t) + kappa*rho2*E(t) - (gamma_alpha + gamma_i)*P(t))`
- Matrix:  `Eq(Derivative(P(t), t), -delta_p*P(t) + kappa*rho_2*E(t) - (gamma_a + gamma_i)*P(t))`
- Difference: `gamma_a*P(t) - gamma_alpha*P(t) + kappa*rho2*E(t) - kappa*rho_2*E(t)`

**Equation 6:**
- Correct: `Eq(Derivative(R(t), t), gamma_i*(I(t) + P(t)) + gamma_r*H(t))`
- Matrix:  `Eq(Derivative(R(t), t), gamma_i*(I(t) + P(t)) + gamma_r*H(t))`
- Difference: `0`

**Equation 7:**
- Correct: `Eq(Derivative(S(t), t), -beta*l*H(t)*S(t)/N - beta*I(t)*S(t)/N - beta_prime*P(t)*S(t)/N)`
- Matrix:  `Eq(Derivative(S(t), t), -beta*l*H(t)*S(t)/N - beta*I(t)*S(t)/N - beta_prime*P(t)*S(t)/N)`
- Difference: `0`

