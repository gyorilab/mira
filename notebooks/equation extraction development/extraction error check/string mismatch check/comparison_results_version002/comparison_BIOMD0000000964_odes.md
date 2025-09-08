
# Comparison by Subtraction
## Model: BIOMD0000000964
### Timestamp: 2025-09-08_13-05-41

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(E(t), t), beta_1*P(t)*S(t)/(alpha_1*P(t) + 1) + beta_2*(I_A(t) + I_S(t))*S(t)/(alpha_2*(I_A(t) + I_S(t)) + 1) - mu*E(t) - omega*E(t) - psi*E(t))`
- Extracted: `Eq(Derivative(E(t), t), beta1*P(t)*S(t)/(alpha1*P(t) + 1) + beta2*(IA(t) + IS(t))*S(t)/(alpha2*(IA(t) + IS(t)) + 1) - mu*E(t) - omega*E(t) - psi*E(t))`
- Difference: `beta1*P(t)*S(t)/(alpha1*P(t) + 1) + beta2*(IA(t) + IS(t))*S(t)/(alpha2*(IA(t) + IS(t)) + 1) - beta_1*P(t)*S(t)/(alpha_1*P(t) + 1) - beta_2*(I_A(t) + I_S(t))*S(t)/(alpha_2*(I_A(t) + I_S(t)) + 1)`

**Equation 1:**
- Correct:   `Eq(Derivative(I_A(t), t), -gamma_A*I_A(t) + omega*(1 - delta)*E(t) - (mu + sigma)*I_A(t))`
- Extracted: `Eq(Derivative(IA(t), t), -gamma*IA(t) + omega*(1 - delta)*E(t) - (mu + sigma)*IA(t))`
- Difference: `-gamma*IA(t) + gamma_A*I_A(t) - (mu + sigma)*IA(t) + (mu + sigma)*I_A(t) - Derivative(IA(t), t) + Derivative(I_A(t), t)`

**Equation 2:**
- Correct:   `Eq(Derivative(I_S(t), t), delta*omega*E(t) - gamma_S*I_S(t) - (mu + sigma)*I_S(t))`
- Extracted: `Eq(Derivative(IS(t), t), delta*omega*E(t) - gamma*IS(t) - (mu + sigma)*IS(t))`
- Difference: `-gamma*IS(t) + gamma_S*I_S(t) - (mu + sigma)*IS(t) + (mu + sigma)*I_S(t) - Derivative(IS(t), t) + Derivative(I_S(t), t)`

**Equation 3:**
- Correct:   `Eq(Derivative(P(t), t), eta_A*I_A(t) + eta_S*I_S(t) - mu_p*P(t))`
- Extracted: `Eq(Derivative(P(t), t), eta*IA(t) + eta*IS(t)*S(t) - mu*P(t))`
- Difference: `eta*IA(t) + eta*IS(t)*S(t) - eta_A*I_A(t) - eta_S*I_S(t) - mu*P(t) + mu_p*P(t)`

**Equation 4:**
- Correct:   `Eq(Derivative(R(t), t), gamma_A*I_A(t) + gamma_S*I_S(t) - mu*R(t))`
- Extracted: `Eq(Derivative(R(t), t), gamma*IA(t) + gamma*IS(t)*S(t) - mu*R(t))`
- Difference: `gamma*IA(t) + gamma*IS(t)*S(t) - gamma_A*I_A(t) - gamma_S*I_S(t)`

**Equation 5:**
- Correct:   `Eq(Derivative(S(t), t), b - beta_1*P(t)*S(t)/(alpha_1*P(t) + 1) - beta_2*(I_A(t) + I_S(t))*S(t)/(alpha_2*(I_A(t) + I_S(t)) + 1) - mu*S(t) + psi*E(t))`
- Extracted: `Eq(Derivative(S(t), t), b - beta1*P(t)*S(t)/(alpha1*P(t) + 1) - beta2*(IA(t) + IS(t))*S(t)/(alpha2*(IA(t) + IS(t)) + 1) - mu*S(t) + psi*E(t))`
- Difference: `-beta1*P(t)*S(t)/(alpha1*P(t) + 1) - beta2*(IA(t) + IS(t))*S(t)/(alpha2*(IA(t) + IS(t)) + 1) + beta_1*P(t)*S(t)/(alpha_1*P(t) + 1) + beta_2*(I_A(t) + I_S(t))*S(t)/(alpha_2*(I_A(t) + I_S(t)) + 1)`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(E(t), t), beta_1*P(t)*S(t)/(alpha_1*P(t) + 1) + beta_2*(I_A(t) + I_S(t))*S(t)/(alpha_2*(I_A(t) + I_S(t)) + 1) - mu*E(t) - omega*E(t) - psi*E(t))`
- Corrected: `Eq(Derivative(E(t), t), beta1*P(t)*S(t)/(alpha1*P(t) + 1) + beta2*(IA(t) + IS(t))*S(t)/(alpha2*(IA(t) + IS(t)) + 1) - mu*E(t) - omega*E(t) - psi*E(t))`
- Difference: `beta1*P(t)*S(t)/(alpha1*P(t) + 1) + beta2*(IA(t) + IS(t))*S(t)/(alpha2*(IA(t) + IS(t)) + 1) - beta_1*P(t)*S(t)/(alpha_1*P(t) + 1) - beta_2*(I_A(t) + I_S(t))*S(t)/(alpha_2*(I_A(t) + I_S(t)) + 1)`

**Equation 1:**
- Correct: `Eq(Derivative(I_A(t), t), -gamma_A*I_A(t) + omega*(1 - delta)*E(t) - (mu + sigma)*I_A(t))`
- Corrected: `Eq(Derivative(IA(t), t), -gamma*IA(t) + omega*(1 - delta)*E(t) - (mu + sigma)*IA(t))`
- Difference: `-gamma*IA(t) + gamma_A*I_A(t) - (mu + sigma)*IA(t) + (mu + sigma)*I_A(t) - Derivative(IA(t), t) + Derivative(I_A(t), t)`

**Equation 2:**
- Correct: `Eq(Derivative(I_S(t), t), delta*omega*E(t) - gamma_S*I_S(t) - (mu + sigma)*I_S(t))`
- Corrected: `Eq(Derivative(IS(t), t), delta*omega*E(t) - gamma*IS(t) - (mu + sigma)*IS(t))`
- Difference: `-gamma*IS(t) + gamma_S*I_S(t) - (mu + sigma)*IS(t) + (mu + sigma)*I_S(t) - Derivative(IS(t), t) + Derivative(I_S(t), t)`

**Equation 3:**
- Correct: `Eq(Derivative(P(t), t), eta_A*I_A(t) + eta_S*I_S(t) - mu_p*P(t))`
- Corrected: `Eq(Derivative(P(t), t), eta*IA(t) + eta*IS(t)*S(t) - mu*P(t))`
- Difference: `eta*IA(t) + eta*IS(t)*S(t) - eta_A*I_A(t) - eta_S*I_S(t) - mu*P(t) + mu_p*P(t)`

**Equation 4:**
- Correct: `Eq(Derivative(R(t), t), gamma_A*I_A(t) + gamma_S*I_S(t) - mu*R(t))`
- Corrected: `Eq(Derivative(R(t), t), gamma*IA(t) + gamma*IS(t)*S(t) - mu*R(t))`
- Difference: `gamma*IA(t) + gamma*IS(t)*S(t) - gamma_A*I_A(t) - gamma_S*I_S(t)`

**Equation 5:**
- Correct: `Eq(Derivative(S(t), t), b - beta_1*P(t)*S(t)/(alpha_1*P(t) + 1) - beta_2*(I_A(t) + I_S(t))*S(t)/(alpha_2*(I_A(t) + I_S(t)) + 1) - mu*S(t) + psi*E(t))`
- Corrected: `Eq(Derivative(S(t), t), b - beta1*P(t)*S(t)/(alpha1*P(t) + 1) - beta2*(IA(t) + IS(t))*S(t)/(alpha2*(IA(t) + IS(t)) + 1) - mu*S(t) + psi*E(t))`
- Difference: `-beta1*P(t)*S(t)/(alpha1*P(t) + 1) - beta2*(IA(t) + IS(t))*S(t)/(alpha2*(IA(t) + IS(t)) + 1) + beta_1*P(t)*S(t)/(alpha_1*P(t) + 1) + beta_2*(I_A(t) + I_S(t))*S(t)/(alpha_2*(I_A(t) + I_S(t)) + 1)`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(E(t), t), beta_1*P(t)*S(t)/(alpha_1*P(t) + 1) + beta_2*(I_A(t) + I_S(t))*S(t)/(alpha_2*(I_A(t) + I_S(t)) + 1) - mu*E(t) - omega*E(t) - psi*E(t))`
- Matrix:  `Eq(Derivative(E(t), t), beta1*P(t)*S(t)/(alpha1*P(t) + 1) + beta2*(IA + IS)*S(t)/(alpha2*(IA + IS) + 1) - delta*omega*E(t) - mu*E(t) - omega*(1 - delta)*E(t) - psi*E(t))`
- Difference: `-beta1*P(t)*S(t)/(alpha1*P(t) + 1) - beta2*(IA + IS)*S(t)/(alpha2*(IA + IS) + 1) + beta_1*P(t)*S(t)/(alpha_1*P(t) + 1) + beta_2*(I_A(t) + I_S(t))*S(t)/(alpha_2*(I_A(t) + I_S(t)) + 1) + delta*omega*E(t) - omega*(delta - 1)*E(t) - omega*E(t)`

**Equation 1:**
- Correct: `Eq(Derivative(I_A(t), t), -gamma_A*I_A(t) + omega*(1 - delta)*E(t) - (mu + sigma)*I_A(t))`
- Matrix:  `Eq(Derivative(IS(t), t), -IS*gamma - IS*(mu + sigma) + delta*omega*E(t))`
- Difference: `IS*gamma + IS*(mu + sigma) - delta*omega*E(t) - gamma_A*I_A(t) - omega*(delta - 1)*E(t) - (mu + sigma)*I_A(t) + Derivative(IS(t), t) - Derivative(I_A(t), t)`

**Equation 2:**
- Correct: `Eq(Derivative(I_S(t), t), delta*omega*E(t) - gamma_S*I_S(t) - (mu + sigma)*I_S(t))`
- Matrix:  `Eq(Derivative(IA(t), t), -IA*gamma - IA*(mu + sigma) + omega*(1 - delta)*E(t))`
- Difference: `IA*gamma + IA*(mu + sigma) + delta*omega*E(t) - gamma_S*I_S(t) + omega*(delta - 1)*E(t) - (mu + sigma)*I_S(t) + Derivative(IA(t), t) - Derivative(I_S(t), t)`

**Equation 3:**
- Correct: `Eq(Derivative(P(t), t), eta_A*I_A(t) + eta_S*I_S(t) - mu_p*P(t))`
- Matrix:  `Eq(Derivative(P(t), t), IA*eta + IS*eta*S(t) - mu*P(t))`
- Difference: `-IA*eta - IS*eta*S(t) + eta_A*I_A(t) + eta_S*I_S(t) + mu*P(t) - mu_p*P(t)`

**Equation 4:**
- Correct: `Eq(Derivative(R(t), t), gamma_A*I_A(t) + gamma_S*I_S(t) - mu*R(t))`
- Matrix:  `Eq(Derivative(R(t), t), IA*gamma + IS*gamma*S(t) - mu*R(t))`
- Difference: `-IA*gamma - IS*gamma*S(t) + gamma_A*I_A(t) + gamma_S*I_S(t)`

**Equation 5:**
- Correct: `Eq(Derivative(S(t), t), b - beta_1*P(t)*S(t)/(alpha_1*P(t) + 1) - beta_2*(I_A(t) + I_S(t))*S(t)/(alpha_2*(I_A(t) + I_S(t)) + 1) - mu*S(t) + psi*E(t))`
- Matrix:  `Eq(Derivative(S(t), t), b - beta1*P(t)*S(t)/(alpha1*P(t) + 1) - beta2*(IA + IS)*S(t)/(alpha2*(IA + IS) + 1) - mu*S(t) + psi*E(t))`
- Difference: `beta1*P(t)*S(t)/(alpha1*P(t) + 1) + beta2*(IA + IS)*S(t)/(alpha2*(IA + IS) + 1) - beta_1*P(t)*S(t)/(alpha_1*P(t) + 1) - beta_2*(I_A(t) + I_S(t))*S(t)/(alpha_2*(I_A(t) + I_S(t)) + 1)`

