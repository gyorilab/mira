
# Comparison by Subtraction
## Model: BIOMD0000000958
### Timestamp: 2025-09-05_14-04-58

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(S(t), t), -beta*l*H(t)*S(t)/N - beta*I(t)*S(t)/N - beta_prime*P(t)*S(t)/N)`
- Extracted: `Eq(Derivative(S(t), t), -beta*l*H(t)*S(t)/N - beta*I(t)*S(t)/N - beta_prime*P(t)*S(t)/N)`
- Difference: `0`
- Match: ✓

**Equation 1:**
- Correct:   `Eq(Derivative(E(t), t), -kappa*E(t) + beta*l*H(t)*S(t)/N + beta*I(t)*S(t)/N + beta_prime*P(t)*S(t)/N)`
- Extracted: `Eq(Derivative(E(t), t), -kappa_1*E(t) + beta*l*H(t)*S(t)/N + beta*I(t)*S(t)/N + beta_prime*P(t)*S(t)/N)`
- Difference: `(kappa - kappa_1)*E(t)`
- Match: ✗

**Equation 2:**
- Correct:   `Eq(Derivative(I(t), t), -delta_i*I(t) + kappa*rho1*E(t) - (gamma_alpha + gamma_i)*I(t))`
- Extracted: `Eq(Derivative(I(t), t), -delta_1*I(t) + kappa_1*rho_1*E(t) - (gamma_alpha + gamma_i)*I(t))`
- Difference: `-delta_1*I(t) + delta_i*I(t) - kappa*rho1*E(t) + kappa_1*rho_1*E(t)`
- Match: ✗

**Equation 3:**
- Correct:   `Eq(Derivative(P(t), t), -delta_p*P(t) + kappa*rho2*E(t) - (gamma_alpha + gamma_i)*P(t))`
- Extracted: `Eq(Derivative(P(t), t), -delta_2*P(t) + kappa_2*rho_2*E(t) - (gamma_alpha + gamma_i)*P(t))`
- Difference: `-delta_2*P(t) + delta_p*P(t) - kappa*rho2*E(t) + kappa_2*rho_2*E(t)`
- Match: ✗

**Equation 4:**
- Correct:   `Eq(Derivative(A(t), t), kappa*(-rho1 - rho2 + 1)*E(t))`
- Extracted: `Eq(Derivative(A(t), t), k*(1 - rho_2)*E(t))`
- Difference: `(-k*(rho_2 - 1) + kappa*(rho1 + rho2 - 1))*E(t)`
- Match: ✗

**Equation 5:**
- Correct:   `Eq(Derivative(H(t), t), -delta_h*H(t) + gamma_alpha*(I(t) + P(t)) - gamma_r*H(t))`
- Extracted: `Eq(Derivative(H(t), t), -delta_H*H(t) + gamma_alpha*(I(t) + P(t)) - gamma_r*H(t))`
- Difference: `(-delta_H + delta_h)*H(t)`
- Match: ✗

**Equation 6:**
- Correct:   `Eq(Derivative(R(t), t), gamma_i*(I(t) + P(t)) + gamma_r*H(t))`
- Extracted: `Eq(Derivative(R(t), t), gamma_i*(I(t) + P(t))*H(t) + gamma_r*H(t))`
- Difference: `gamma_i*(H(t) - 1)*(I(t) + P(t))`
- Match: ✗

**Equation 7:**
- Correct:   `Eq(Derivative(F(t), t), delta_h*H(t) + delta_i*I(t) + delta_p*P(t))`
- Extracted: `Eq(Derivative(F(t), t), delta_1*I(t) + delta_2*H(t)*P(t) + delta_H*H(t))`
- Difference: `delta_1*I(t) + delta_2*H(t)*P(t) + delta_H*H(t) - delta_h*H(t) - delta_i*I(t) - delta_p*P(t)`
- Match: ✗

## 2. correct_odes vs checked_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(S(t), t), -beta*l*H(t)*S(t)/N - beta*I(t)*S(t)/N - beta_prime*P(t)*S(t)/N)`
- Checked: `Eq(Derivative(S(t), t), -beta*l*H(t)*S(t)/N - beta*I(t)*S(t)/N - beta_prime*P(t)*S(t)/N)`
- Difference: `0`
- Match: ✓

**Equation 1:**
- Correct: `Eq(Derivative(E(t), t), -kappa*E(t) + beta*l*H(t)*S(t)/N + beta*I(t)*S(t)/N + beta_prime*P(t)*S(t)/N)`
- Checked: `Eq(Derivative(E(t), t), -kappa_1*E(t) + beta*l*H(t)*S(t)/N + beta*I(t)*S(t)/N + beta_prime*P(t)*S(t)/N)`
- Difference: `(kappa - kappa_1)*E(t)`
- Match: ✗

**Equation 2:**
- Correct: `Eq(Derivative(I(t), t), -delta_i*I(t) + kappa*rho1*E(t) - (gamma_alpha + gamma_i)*I(t))`
- Checked: `Eq(Derivative(I(t), t), -delta_1*I(t) + kappa_1*rho_1*E(t) - (gamma_alpha + gamma_i)*I(t))`
- Difference: `-delta_1*I(t) + delta_i*I(t) - kappa*rho1*E(t) + kappa_1*rho_1*E(t)`
- Match: ✗

**Equation 3:**
- Correct: `Eq(Derivative(P(t), t), -delta_p*P(t) + kappa*rho2*E(t) - (gamma_alpha + gamma_i)*P(t))`
- Checked: `Eq(Derivative(P(t), t), -delta_2*P(t) + kappa_2*rho_2*E(t) - (gamma_alpha + gamma_i)*P(t))`
- Difference: `-delta_2*P(t) + delta_p*P(t) - kappa*rho2*E(t) + kappa_2*rho_2*E(t)`
- Match: ✗

**Equation 4:**
- Correct: `Eq(Derivative(A(t), t), kappa*(-rho1 - rho2 + 1)*E(t))`
- Checked: `Eq(Derivative(A(t), t), k*(1 - rho_2)*E(t))`
- Difference: `(-k*(rho_2 - 1) + kappa*(rho1 + rho2 - 1))*E(t)`
- Match: ✗

**Equation 5:**
- Correct: `Eq(Derivative(H(t), t), -delta_h*H(t) + gamma_alpha*(I(t) + P(t)) - gamma_r*H(t))`
- Checked: `Eq(Derivative(H(t), t), -delta_H*H(t) + gamma_alpha*(I(t) + P(t)) - gamma_r*H(t))`
- Difference: `(-delta_H + delta_h)*H(t)`
- Match: ✗

**Equation 6:**
- Correct: `Eq(Derivative(R(t), t), gamma_i*(I(t) + P(t)) + gamma_r*H(t))`
- Checked: `Eq(Derivative(R(t), t), gamma_i*(I(t) + P(t))*H(t) + gamma_r*H(t))`
- Difference: `gamma_i*(H(t) - 1)*(I(t) + P(t))`
- Match: ✗

**Equation 7:**
- Correct: `Eq(Derivative(F(t), t), delta_h*H(t) + delta_i*I(t) + delta_p*P(t))`
- Checked: `Eq(Derivative(F(t), t), delta_1*I(t) + delta_2*H(t)*P(t) + delta_H*H(t))`
- Difference: `delta_1*I(t) + delta_2*H(t)*P(t) + delta_H*H(t) - delta_h*H(t) - delta_i*I(t) - delta_p*P(t)`
- Match: ✗

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(S(t), t), -beta*l*H(t)*S(t)/N - beta*I(t)*S(t)/N - beta_prime*P(t)*S(t)/N)`
- Matrix:  `Eq(Derivative(E, t), -E*kappa_1 + H*S*beta*l/N + I*S*beta/N + P*S*beta_prime/N)`
- Difference: `(-H*S*beta*l - I*S*beta + N*(E*kappa_1 - Derivative(S(t), t)) - P*S*beta_prime - beta*l*H(t)*S(t) - beta*I(t)*S(t) - beta_prime*P(t)*S(t))/N`
- Match: ✗

**Equation 1:**
- Correct: `Eq(Derivative(E(t), t), -kappa*E(t) + beta*l*H(t)*S(t)/N + beta*I(t)*S(t)/N + beta_prime*P(t)*S(t)/N)`
- Matrix:  `Eq(Derivative(A, t), E*k*(1 - rho_2))`
- Difference: `(N*(E*k*(rho_2 - 1) - kappa*E(t) - Derivative(E(t), t)) + beta*l*H(t)*S(t) + beta*I(t)*S(t) + beta_prime*P(t)*S(t))/N`
- Match: ✗

**Equation 2:**
- Correct: `Eq(Derivative(I(t), t), -delta_i*I(t) + kappa*rho1*E(t) - (gamma_alpha + gamma_i)*I(t))`
- Matrix:  `Eq(Derivative(P, t), E*kappa_2*rho_2 - P*delta_2 - P*(gamma_alpha + gamma_i))`
- Difference: `-E*kappa_2*rho_2 + P*delta_2 + P*(gamma_alpha + gamma_i) - delta_i*I(t) + kappa*rho1*E(t) - (gamma_alpha + gamma_i)*I(t) - Derivative(I(t), t)`
- Match: ✗

**Equation 3:**
- Correct: `Eq(Derivative(P(t), t), -delta_p*P(t) + kappa*rho2*E(t) - (gamma_alpha + gamma_i)*P(t))`
- Matrix:  `Eq(Derivative(I, t), E*kappa_1*rho_1 - I*delta_1 - I*(gamma_alpha + gamma_i))`
- Difference: `-E*kappa_1*rho_1 + I*delta_1 + I*(gamma_alpha + gamma_i) - delta_p*P(t) + kappa*rho2*E(t) - (gamma_alpha + gamma_i)*P(t) - Derivative(P(t), t)`
- Match: ✗

**Equation 4:**
- Correct: `Eq(Derivative(A(t), t), kappa*(-rho1 - rho2 + 1)*E(t))`
- Matrix:  `Eq(Derivative(H, t), -H*delta_H - H*gamma_r + gamma_alpha*(I + P))`
- Difference: `H*delta_H + H*gamma_r - gamma_alpha*(I + P) - kappa*(rho1 + rho2 - 1)*E(t) - Derivative(A(t), t)`
- Match: ✗

**Equation 5:**
- Correct: `Eq(Derivative(H(t), t), -delta_h*H(t) + gamma_alpha*(I(t) + P(t)) - gamma_r*H(t))`
- Matrix:  `Eq(Derivative(F, t), H*P*delta_2 + H*delta_H + I*delta_1)`
- Difference: `-H*P*delta_2 - H*delta_H - I*delta_1 - delta_h*H(t) + gamma_alpha*(I(t) + P(t)) - gamma_r*H(t) - Derivative(H(t), t)`
- Match: ✗

**Equation 6:**
- Correct: `Eq(Derivative(R(t), t), gamma_i*(I(t) + P(t)) + gamma_r*H(t))`
- Matrix:  `Eq(Derivative(R, t), H*gamma_i*(I + P) + H*gamma_r)`
- Difference: `-H*gamma_i*(I + P) - H*gamma_r + gamma_i*(I(t) + P(t)) + gamma_r*H(t) - Derivative(R(t), t)`
- Match: ✗

**Equation 7:**
- Correct: `Eq(Derivative(F(t), t), delta_h*H(t) + delta_i*I(t) + delta_p*P(t))`
- Matrix:  `Eq(Derivative(S, t), -H*S*beta*l/N - I*S*beta/N - P*S*beta_prime/N)`
- Difference: `(H*S*beta*l + I*S*beta + N*(delta_h*H(t) + delta_i*I(t) + delta_p*P(t) - Derivative(F(t), t)) + P*S*beta_prime)/N`
- Match: ✗

## Summary
- Extracted: 1/8 equations match
- Checked: 1/8 equations match
- Matrix: 0/8 equations match

---

