
# Comparison by Subtraction
## Model: 2024_dec_epi_1_model_A
### Timestamp: 2025-09-08_14-59-57

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(s1(t), t), -lambda_h*nu*s1(t) - mu_h*s1(t) + pi_h*(1 - rho))`
- Extracted: `Eq(Derivative(Eh(t), t), lambd*v*(S1(t) + Sh(t)) - (mu + nu + sigma)*Eh(t))`
- Difference: `lambd*v*(S1(t) + Sh(t)) + lambda_h*nu*s1(t) + mu_h*s1(t) + pi_h*(rho - 1) - (mu + nu + sigma)*Eh(t) - Derivative(Eh(t), t) + Derivative(s1(t), t)`

**Equation 1:**
- Correct:   `Eq(Derivative(s_h(t), t), -lambda_h*s_h(t) + mu_h*rho - mu_h*s_h(t))`
- Extracted: `Eq(Derivative(Er(t), t), lambd*Sr(t) - (mu + sigma_r)*Er(t))`
- Difference: `lambd*Sr(t) + lambda_h*s_h(t) - mu_h*rho + mu_h*s_h(t) - (mu + sigma_r)*Er(t) - Derivative(Er(t), t) + Derivative(s_h(t), t)`

**Equation 2:**
- Correct:   `Eq(Derivative(e_h(t), t), lambda_h*(nu*s1(t) + s_h(t)) - (mu_h + sigma)*e_h(t))`
- Extracted: `Eq(Derivative(H(t), t), delta_h + k1*I1(t) - k2*I2(t) + mu*H(t))`
- Difference: `delta_h + k1*I1(t) - k2*I2(t) - lambda_h*(nu*s1(t) + s_h(t)) + mu*H(t) + (mu_h + sigma)*e_h(t) - Derivative(H(t), t) + Derivative(e_h(t), t)`

**Equation 3:**
- Correct:   `Eq(Derivative(p(t), t), sigma*e_h(t) - (mu_h + omega)*p(t))`
- Extracted: `Eq(Derivative(I1(t), t), omega*P(t) - (k1 + mu + tau1 + tau2)*I1(t))`
- Difference: `omega*P(t) - sigma*e_h(t) + (mu_h + omega)*p(t) - (k1 + mu + tau1 + tau2)*I1(t) - Derivative(I1(t), t) + Derivative(p(t), t)`

**Equation 4:**
- Correct:   `Eq(Derivative(i1(t), t), omega*p(t) - (k1 + mu_h + tau1 + theta)*i1(t))`
- Extracted: `Eq(Derivative(I2(t), t), theta1*(delta1 + k2 + mu + tau2 + tau3)*H(t))`
- Difference: `-omega*p(t) + theta1*(delta1 + k2 + mu + tau2 + tau3)*H(t) + (k1 + mu_h + tau1 + theta)*i1(t) - Derivative(I2(t), t) + Derivative(i1(t), t)`

**Equation 5:**
- Correct:   `Eq(Derivative(i2(t), t), theta*i1(t) - (delta_i + k2 + mu_h + tau2)*i2(t))`
- Extracted: `Eq(Derivative(Ir(t), t), sigma_r*Er(t) - (delta_r + mu + tau_r)*Ir(t))`
- Difference: `sigma_r*Er(t) - theta*i1(t) - (delta_r + mu + tau_r)*Ir(t) + (delta_i + k2 + mu_h + tau2)*i2(t) - Derivative(Ir(t), t) + Derivative(i2(t), t)`

**Equation 6:**
- Correct:   `Eq(Derivative(h(t), t), k1*i1(t) + k2*i2(t) - (delta_h + mu_h + tau3)*h(t))`
- Extracted: `Eq(Derivative(P(t), t), sigma*Eh(t) - (mu + omega)*P(t))`
- Difference: `-k1*i1(t) - k2*i2(t) + sigma*Eh(t) - (mu + omega)*P(t) + (delta_h + mu_h + tau3)*h(t) - Derivative(P(t), t) + Derivative(h(t), t)`

**Equation 7:**
- Correct:   `Eq(Derivative(r_h(t), t), -mu_h*r_h(t) + tau1*i1(t) + tau2*i2(t) + tau3*h(t))`
- Extracted: `Eq(Derivative(R(t), t), k1*I1(t) - mu*R(t) + tau2*H(t))`
- Difference: `k1*I1(t) - mu*R(t) + mu_h*r_h(t) - tau1*i1(t) + tau2*H(t) - tau2*i2(t) - tau3*h(t) - Derivative(R(t), t) + Derivative(r_h(t), t)`

**Equation 8:**
- Correct:   `Eq(Derivative(s_r(t), t), -lambda_r*s_r(t) - mu_r*s_r(t) + pi_r)`
- Extracted: `Eq(Derivative(Rr(t), t), -mu*Rr(t) + tau_r*Ir(t))`
- Difference: `lambda_r*s_r(t) - mu*Rr(t) + mu_r*s_r(t) - pi_r + tau_r*Ir(t) - Derivative(Rr(t), t) + Derivative(s_r(t), t)`

**Equation 9:**
- Correct:   `Eq(Derivative(e_r(t), t), lambda_r*s_r(t) - (mu_r + sigma_r)*e_r(t))`
- Extracted: `Eq(Derivative(S1(t), t), -lambd*nu*S1(t) - mu*S1(t) + pi*(1 - rho))`
- Difference: `-lambd*nu*S1(t) - lambda_r*s_r(t) - mu*S1(t) - pi*(rho - 1) + (mu_r + sigma_r)*e_r(t) - Derivative(S1(t), t) + Derivative(e_r(t), t)`

**Equation 10:**
- Correct:   `Eq(Derivative(i_r(t), t), sigma_r*e_r(t) - (delta_r + mu_r + tau_r)*i_r(t))`
- Extracted: `Eq(Derivative(Sh(t), t), -lambd*Sh(t) + mu*rho*Sh(t))`
- Difference: `-lambd*Sh(t) + mu*rho*Sh(t) - sigma_r*e_r(t) + (delta_r + mu_r + tau_r)*i_r(t) - Derivative(Sh(t), t) + Derivative(i_r(t), t)`

**Equation 11:**
- Correct:   `Eq(Derivative(r_r(t), t), -mu_r*r_r(t) + tau_r*i_r(t))`
- Extracted: `Eq(Derivative(Sr(t), t), -lambd*Sr(t) - mu*Sr(t) + pi*rho)`
- Difference: `-lambd*Sr(t) - mu*Sr(t) + mu_r*r_r(t) + pi*rho - tau_r*i_r(t) - Derivative(Sr(t), t) + Derivative(r_r(t), t)`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(s1(t), t), -lambda_h*nu*s1(t) - mu_h*s1(t) + pi_h*(1 - rho))`
- Corrected: `Eq(Derivative(Eh(t), t), lambd*v*(S1(t) + Sh(t)) - (mu + nu + sigma)*Eh(t))`
- Difference: `lambd*v*(S1(t) + Sh(t)) + lambda_h*nu*s1(t) + mu_h*s1(t) + pi_h*(rho - 1) - (mu + nu + sigma)*Eh(t) - Derivative(Eh(t), t) + Derivative(s1(t), t)`

**Equation 1:**
- Correct: `Eq(Derivative(s_h(t), t), -lambda_h*s_h(t) + mu_h*rho - mu_h*s_h(t))`
- Corrected: `Eq(Derivative(Er(t), t), lambd*Sr(t) - (mu + sigma_r)*Er(t))`
- Difference: `lambd*Sr(t) + lambda_h*s_h(t) - mu_h*rho + mu_h*s_h(t) - (mu + sigma_r)*Er(t) - Derivative(Er(t), t) + Derivative(s_h(t), t)`

**Equation 2:**
- Correct: `Eq(Derivative(e_h(t), t), lambda_h*(nu*s1(t) + s_h(t)) - (mu_h + sigma)*e_h(t))`
- Corrected: `Eq(Derivative(H(t), t), delta_h + k1*I1(t) - k2*I2(t) + mu*H(t))`
- Difference: `delta_h + k1*I1(t) - k2*I2(t) - lambda_h*(nu*s1(t) + s_h(t)) + mu*H(t) + (mu_h + sigma)*e_h(t) - Derivative(H(t), t) + Derivative(e_h(t), t)`

**Equation 3:**
- Correct: `Eq(Derivative(p(t), t), sigma*e_h(t) - (mu_h + omega)*p(t))`
- Corrected: `Eq(Derivative(I1(t), t), omega*P(t) - (k1 + mu + tau1 + tau2)*I1(t))`
- Difference: `omega*P(t) - sigma*e_h(t) + (mu_h + omega)*p(t) - (k1 + mu + tau1 + tau2)*I1(t) - Derivative(I1(t), t) + Derivative(p(t), t)`

**Equation 4:**
- Correct: `Eq(Derivative(i1(t), t), omega*p(t) - (k1 + mu_h + tau1 + theta)*i1(t))`
- Corrected: `Eq(Derivative(I2(t), t), theta1*(delta1 + k2 + mu + tau2 + tau3)*H(t))`
- Difference: `-omega*p(t) + theta1*(delta1 + k2 + mu + tau2 + tau3)*H(t) + (k1 + mu_h + tau1 + theta)*i1(t) - Derivative(I2(t), t) + Derivative(i1(t), t)`

**Equation 5:**
- Correct: `Eq(Derivative(i2(t), t), theta*i1(t) - (delta_i + k2 + mu_h + tau2)*i2(t))`
- Corrected: `Eq(Derivative(Ir(t), t), sigma_r*Er(t) - (delta_r + mu + tau_r)*Ir(t))`
- Difference: `sigma_r*Er(t) - theta*i1(t) - (delta_r + mu + tau_r)*Ir(t) + (delta_i + k2 + mu_h + tau2)*i2(t) - Derivative(Ir(t), t) + Derivative(i2(t), t)`

**Equation 6:**
- Correct: `Eq(Derivative(h(t), t), k1*i1(t) + k2*i2(t) - (delta_h + mu_h + tau3)*h(t))`
- Corrected: `Eq(Derivative(P(t), t), sigma*Eh(t) - (mu + omega)*P(t))`
- Difference: `-k1*i1(t) - k2*i2(t) + sigma*Eh(t) - (mu + omega)*P(t) + (delta_h + mu_h + tau3)*h(t) - Derivative(P(t), t) + Derivative(h(t), t)`

**Equation 7:**
- Correct: `Eq(Derivative(r_h(t), t), -mu_h*r_h(t) + tau1*i1(t) + tau2*i2(t) + tau3*h(t))`
- Corrected: `Eq(Derivative(R(t), t), k1*I1(t) - mu*R(t) + tau2*H(t))`
- Difference: `k1*I1(t) - mu*R(t) + mu_h*r_h(t) - tau1*i1(t) + tau2*H(t) - tau2*i2(t) - tau3*h(t) - Derivative(R(t), t) + Derivative(r_h(t), t)`

**Equation 8:**
- Correct: `Eq(Derivative(s_r(t), t), -lambda_r*s_r(t) - mu_r*s_r(t) + pi_r)`
- Corrected: `Eq(Derivative(Rr(t), t), -mu*Rr(t) + tau_r*Ir(t))`
- Difference: `lambda_r*s_r(t) - mu*Rr(t) + mu_r*s_r(t) - pi_r + tau_r*Ir(t) - Derivative(Rr(t), t) + Derivative(s_r(t), t)`

**Equation 9:**
- Correct: `Eq(Derivative(e_r(t), t), lambda_r*s_r(t) - (mu_r + sigma_r)*e_r(t))`
- Corrected: `Eq(Derivative(S1(t), t), -lambd*nu*S1(t) - mu*S1(t) + pi*(1 - rho))`
- Difference: `-lambd*nu*S1(t) - lambda_r*s_r(t) - mu*S1(t) - pi*(rho - 1) + (mu_r + sigma_r)*e_r(t) - Derivative(S1(t), t) + Derivative(e_r(t), t)`

**Equation 10:**
- Correct: `Eq(Derivative(i_r(t), t), sigma_r*e_r(t) - (delta_r + mu_r + tau_r)*i_r(t))`
- Corrected: `Eq(Derivative(Sh(t), t), -lambd*Sh(t) + mu*rho*Sh(t))`
- Difference: `-lambd*Sh(t) + mu*rho*Sh(t) - sigma_r*e_r(t) + (delta_r + mu_r + tau_r)*i_r(t) - Derivative(Sh(t), t) + Derivative(i_r(t), t)`

**Equation 11:**
- Correct: `Eq(Derivative(r_r(t), t), -mu_r*r_r(t) + tau_r*i_r(t))`
- Corrected: `Eq(Derivative(Sr(t), t), -lambd*Sr(t) - mu*Sr(t) + pi*rho)`
- Difference: `-lambd*Sr(t) - mu*Sr(t) + mu_r*r_r(t) + pi*rho - tau_r*i_r(t) - Derivative(Sr(t), t) + Derivative(r_r(t), t)`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(s1(t), t), -lambda_h*nu*s1(t) - mu_h*s1(t) + pi_h*(1 - rho))`
- Matrix:  `Eq(Derivative(Eh(t), t), -Eh*(mu + nu + sigma) + lambd*v*(S1 + Sh))`
- Difference: `Eh*(mu + nu + sigma) - lambd*v*(S1 + Sh) - lambda_h*nu*s1(t) - mu_h*s1(t) - pi_h*(rho - 1) + Derivative(Eh(t), t) - Derivative(s1(t), t)`

**Equation 1:**
- Correct: `Eq(Derivative(s_h(t), t), -lambda_h*s_h(t) + mu_h*rho - mu_h*s_h(t))`
- Matrix:  `Eq(Derivative(Er(t), t), -Er*(mu + sigma_r) + Sr*lambd)`
- Difference: `Er*(mu + sigma_r) - Sr*lambd - lambda_h*s_h(t) + mu_h*rho - mu_h*s_h(t) + Derivative(Er(t), t) - Derivative(s_h(t), t)`

**Equation 2:**
- Correct: `Eq(Derivative(e_h(t), t), lambda_h*(nu*s1(t) + s_h(t)) - (mu_h + sigma)*e_h(t))`
- Matrix:  `Eq(Derivative(H(t), t), I1*k1 - I2*k2 + delta_h + mu*H(t))`
- Difference: `-I1*k1 + I2*k2 - delta_h + lambda_h*(nu*s1(t) + s_h(t)) - mu*H(t) - (mu_h + sigma)*e_h(t) + Derivative(H(t), t) - Derivative(e_h(t), t)`

**Equation 3:**
- Correct: `Eq(Derivative(p(t), t), sigma*e_h(t) - (mu_h + omega)*p(t))`
- Matrix:  `Eq(Derivative(Ir(t), t), Er*sigma_r - Ir*(delta_r + mu + tau_r))`
- Difference: `-Er*sigma_r + Ir*(delta_r + mu + tau_r) + sigma*e_h(t) - (mu_h + omega)*p(t) + Derivative(Ir(t), t) - Derivative(p(t), t)`

**Equation 4:**
- Correct: `Eq(Derivative(i1(t), t), omega*p(t) - (k1 + mu_h + tau1 + theta)*i1(t))`
- Matrix:  `Eq(Derivative(I2(t), t), theta1*(delta1 + k2 + mu + tau2 + tau3)*H(t))`
- Difference: `omega*p(t) - theta1*(delta1 + k2 + mu + tau2 + tau3)*H(t) - (k1 + mu_h + tau1 + theta)*i1(t) + Derivative(I2(t), t) - Derivative(i1(t), t)`

**Equation 5:**
- Correct: `Eq(Derivative(i2(t), t), theta*i1(t) - (delta_i + k2 + mu_h + tau2)*i2(t))`
- Matrix:  `Eq(Derivative(I1(t), t), -I1*(k1 + mu + tau1 + tau2) + omega*P(t))`
- Difference: `I1*(k1 + mu + tau1 + tau2) - omega*P(t) + theta*i1(t) - (delta_i + k2 + mu_h + tau2)*i2(t) + Derivative(I1(t), t) - Derivative(i2(t), t)`

**Equation 6:**
- Correct: `Eq(Derivative(h(t), t), k1*i1(t) + k2*i2(t) - (delta_h + mu_h + tau3)*h(t))`
- Matrix:  `Eq(Derivative(P(t), t), Eh*sigma - (mu + omega)*P(t))`
- Difference: `-Eh*sigma + k1*i1(t) + k2*i2(t) + (mu + omega)*P(t) - (delta_h + mu_h + tau3)*h(t) + Derivative(P(t), t) - Derivative(h(t), t)`

**Equation 7:**
- Correct: `Eq(Derivative(r_h(t), t), -mu_h*r_h(t) + tau1*i1(t) + tau2*i2(t) + tau3*h(t))`
- Matrix:  `Eq(Derivative(R(t), t), I1*k1 - mu*R(t) + tau2*H(t))`
- Difference: `-I1*k1 + mu*R(t) - mu_h*r_h(t) + tau1*i1(t) - tau2*H(t) + tau2*i2(t) + tau3*h(t) + Derivative(R(t), t) - Derivative(r_h(t), t)`

**Equation 8:**
- Correct: `Eq(Derivative(s_r(t), t), -lambda_r*s_r(t) - mu_r*s_r(t) + pi_r)`
- Matrix:  `Eq(Derivative(Rr(t), t), Ir*tau_r - Rr*mu)`
- Difference: `-Ir*tau_r + Rr*mu - lambda_r*s_r(t) - mu_r*s_r(t) + pi_r + Derivative(Rr(t), t) - Derivative(s_r(t), t)`

**Equation 9:**
- Correct: `Eq(Derivative(e_r(t), t), lambda_r*s_r(t) - (mu_r + sigma_r)*e_r(t))`
- Matrix:  `Eq(Derivative(Sr(t), t), -Sr*lambd - Sr*mu + pi*rho)`
- Difference: `Sr*lambd + Sr*mu + lambda_r*s_r(t) - pi*rho - (mu_r + sigma_r)*e_r(t) + Derivative(Sr(t), t) - Derivative(e_r(t), t)`

**Equation 10:**
- Correct: `Eq(Derivative(i_r(t), t), sigma_r*e_r(t) - (delta_r + mu_r + tau_r)*i_r(t))`
- Matrix:  `Eq(Derivative(S1(t), t), -S1*lambd*nu - S1*mu + pi*(1 - rho))`
- Difference: `S1*lambd*nu + S1*mu + pi*(rho - 1) + sigma_r*e_r(t) - (delta_r + mu_r + tau_r)*i_r(t) + Derivative(S1(t), t) - Derivative(i_r(t), t)`

**Equation 11:**
- Correct: `Eq(Derivative(r_r(t), t), -mu_r*r_r(t) + tau_r*i_r(t))`
- Matrix:  `Eq(Derivative(Sh(t), t), -Sh*lambd + Sh*mu*rho)`
- Difference: `Sh*lambd - Sh*mu*rho - mu_r*r_r(t) + tau_r*i_r(t) + Derivative(Sh(t), t) - Derivative(r_r(t), t)`

