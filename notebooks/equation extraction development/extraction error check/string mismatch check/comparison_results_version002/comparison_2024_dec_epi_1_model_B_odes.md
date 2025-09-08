
# Comparison by Subtraction
## Model: 2024_dec_epi_1_model_B
### Timestamp: 2025-09-08_15-05-16

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(sh(t), t), beta_h - mu_h*sh(t) + phi*qh(t) - (beta_1*ir(t) + beta_2*ih(t))*sh(t)/N_h)`
- Extracted: `Eq(Derivative(Eh(t), t), -(alpha_1 + alpha_2 + mu_h)*Eh(t) + alpha_1*(beta_1*Ih(t) + It(t))/N_h)`
- Difference: `(N_h*(-beta_h + mu_h*sh(t) - phi*qh(t) - (alpha_1 + alpha_2 + mu_h)*Eh(t) - Derivative(Eh(t), t) + Derivative(sh(t), t)) + alpha_1*(beta_1*Ih(t) + It(t)) + (beta_1*ir(t) + beta_2*ih(t))*sh(t))/N_h`

**Equation 1:**
- Correct:   `Eq(Derivative(eh(t), t), -(alpha_1 + alpha_2 + mu_h)*eh(t) + (beta_1*ir(t) + beta_2*ih(t))*sh(t)/N_h)`
- Extracted: `Eq(Derivative(Et(t), t), -(alpha_3 + mu_t)*Et(t) + beta_2*It(t)*St(t)/N_t)`
- Difference: `(N_h*N_t*(-(alpha_3 + mu_t)*Et(t) + (alpha_1 + alpha_2 + mu_h)*eh(t) - Derivative(Et(t), t) + Derivative(eh(t), t)) + N_h*beta_2*It(t)*St(t) - N_t*(beta_1*ir(t) + beta_2*ih(t))*sh(t))/(N_h*N_t)`

**Equation 2:**
- Correct:   `Eq(Derivative(ih(t), t), alpha_1*eh(t) - (delta_h + gamma + mu_h)*ih(t))`
- Extracted: `Eq(Derivative(Ih(t), t), alpha_2*Eh(t) - (gamma_h + mu_h + phi)*Qh(t))`
- Difference: `-alpha_1*eh(t) + alpha_2*Eh(t) + (delta_h + gamma + mu_h)*ih(t) - (gamma_h + mu_h + phi)*Qh(t) - Derivative(Ih(t), t) + Derivative(ih(t), t)`

**Equation 3:**
- Correct:   `Eq(Derivative(qh(t), t), alpha_2*eh(t) - (delta_h + mu_h + phi + tau)*qh(t))`
- Extracted: `Eq(Derivative(Ih(t), t), alpha_3*Et(t) - mu_t*It(t))`
- Difference: `-alpha_2*eh(t) + alpha_3*Et(t) - mu_t*It(t) + (delta_h + mu_h + phi + tau)*qh(t) - Derivative(Ih(t), t) + Derivative(qh(t), t)`

**Equation 4:**
- Correct:   `Eq(Derivative(rh(t), t), gamma*qh(t) - mu_h*rh(t) + tau*qh(t))`
- Extracted: `Eq(Derivative(Rt(t), t), alpha_3*Et(t) - mu_t*Rt(t))`
- Difference: `alpha_3*Et(t) - gamma*qh(t) + mu_h*rh(t) - mu_t*Rt(t) - tau*qh(t) - Derivative(Rt(t), t) + Derivative(rh(t), t)`

**Equation 5:**
- Correct:   `Eq(Derivative(sr(t), t), beta_r - mu_r*sr(t) - beta_3*ir(t)*sr(t)/N_r)`
- Extracted: `Eq(Derivative(Sh(t), t), -mu_h*Sh(t) + phi*Qh(t) + (beta_1*It(t) + beta_2*Ih(t))/N_h)`
- Difference: `-beta_r - mu_h*Sh(t) + mu_r*sr(t) + phi*Qh(t) - Derivative(Sh(t), t) + Derivative(sr(t), t) + beta_3*ir(t)*sr(t)/N_r + beta_1*It(t)/N_h + beta_2*Ih(t)/N_h`

**Equation 6:**
- Correct:   `Eq(Derivative(er(t), t), -(alpha_3 + mu_r)*er(t) + beta_3*ir(t)*sr(t)/N_r)`
- Extracted: `Eq(Derivative(St(t), t), mu_t*St(t) - beta_2*It(t)*St(t)/N_t)`
- Difference: `alpha_3*er(t) + mu_r*er(t) + mu_t*St(t) - Derivative(St(t), t) + Derivative(er(t), t) - beta_2*It(t)*St(t)/N_t - beta_3*ir(t)*sr(t)/N_r`

**Equation 7:**
- Correct:   `Eq(Derivative(ir(t), t), alpha_3*er(t) - (delta_r + mu_r)*ir(t))`
- Extracted: `Eq(Derivative(Qh(t), t), gamma_h*Rh(t) - mu_h*Qh(t))`
- Difference: `-alpha_3*er(t) + gamma_h*Rh(t) - mu_h*Qh(t) + (delta_r + mu_r)*ir(t) - Derivative(Qh(t), t) + Derivative(ir(t), t)`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(sh(t), t), beta_h - mu_h*sh(t) + phi*qh(t) - (beta_1*ir(t) + beta_2*ih(t))*sh(t)/N_h)`
- Corrected: `Eq(Derivative(Eh(t), t), -(alpha_1 + alpha_2 + mu_h)*Eh(t) + alpha_1*(beta_1*Ih(t) + It(t))/N_h)`
- Difference: `(N_h*(-beta_h + mu_h*sh(t) - phi*qh(t) - (alpha_1 + alpha_2 + mu_h)*Eh(t) - Derivative(Eh(t), t) + Derivative(sh(t), t)) + alpha_1*(beta_1*Ih(t) + It(t)) + (beta_1*ir(t) + beta_2*ih(t))*sh(t))/N_h`

**Equation 1:**
- Correct: `Eq(Derivative(eh(t), t), -(alpha_1 + alpha_2 + mu_h)*eh(t) + (beta_1*ir(t) + beta_2*ih(t))*sh(t)/N_h)`
- Corrected: `Eq(Derivative(Et(t), t), -(alpha_3 + mu_t)*Et(t) + beta_2*It(t)*St(t)/N_t)`
- Difference: `(N_h*N_t*(-(alpha_3 + mu_t)*Et(t) + (alpha_1 + alpha_2 + mu_h)*eh(t) - Derivative(Et(t), t) + Derivative(eh(t), t)) + N_h*beta_2*It(t)*St(t) - N_t*(beta_1*ir(t) + beta_2*ih(t))*sh(t))/(N_h*N_t)`

**Equation 2:**
- Correct: `Eq(Derivative(ih(t), t), alpha_1*eh(t) - (delta_h + gamma + mu_h)*ih(t))`
- Corrected: `Eq(Derivative(Ih(t), t), alpha_2*Eh(t) - (gamma_h + mu_h + phi)*Qh(t))`
- Difference: `-alpha_1*eh(t) + alpha_2*Eh(t) + (delta_h + gamma + mu_h)*ih(t) - (gamma_h + mu_h + phi)*Qh(t) - Derivative(Ih(t), t) + Derivative(ih(t), t)`

**Equation 3:**
- Correct: `Eq(Derivative(qh(t), t), alpha_2*eh(t) - (delta_h + mu_h + phi + tau)*qh(t))`
- Corrected: `Eq(Derivative(It(t), t), alpha_3*Et(t) - mu_t*It(t))`
- Difference: `-alpha_2*eh(t) + alpha_3*Et(t) - mu_t*It(t) + (delta_h + mu_h + phi + tau)*qh(t) - Derivative(It(t), t) + Derivative(qh(t), t)`

**Equation 4:**
- Correct: `Eq(Derivative(rh(t), t), gamma*qh(t) - mu_h*rh(t) + tau*qh(t))`
- Corrected: `Eq(Derivative(Rt(t), t), alpha_3*Et(t) - mu_t*Rt(t))`
- Difference: `alpha_3*Et(t) - gamma*qh(t) + mu_h*rh(t) - mu_t*Rt(t) - tau*qh(t) - Derivative(Rt(t), t) + Derivative(rh(t), t)`

**Equation 5:**
- Correct: `Eq(Derivative(sr(t), t), beta_r - mu_r*sr(t) - beta_3*ir(t)*sr(t)/N_r)`
- Corrected: `Eq(Derivative(Sh(t), t), -mu_h*Sh(t) + phi*Qh(t) + (beta_1*It(t) + beta_2*Ih(t))/N_h)`
- Difference: `-beta_r - mu_h*Sh(t) + mu_r*sr(t) + phi*Qh(t) - Derivative(Sh(t), t) + Derivative(sr(t), t) + beta_3*ir(t)*sr(t)/N_r + beta_1*It(t)/N_h + beta_2*Ih(t)/N_h`

**Equation 6:**
- Correct: `Eq(Derivative(er(t), t), -(alpha_3 + mu_r)*er(t) + beta_3*ir(t)*sr(t)/N_r)`
- Corrected: `Eq(Derivative(St(t), t), mu_t*St(t) - beta_2*It(t)*St(t)/N_t)`
- Difference: `alpha_3*er(t) + mu_r*er(t) + mu_t*St(t) - Derivative(St(t), t) + Derivative(er(t), t) - beta_2*It(t)*St(t)/N_t - beta_3*ir(t)*sr(t)/N_r`

**Equation 7:**
- Correct: `Eq(Derivative(ir(t), t), alpha_3*er(t) - (delta_r + mu_r)*ir(t))`
- Corrected: `Eq(Derivative(Qh(t), t), gamma_h*Rh(t) - mu_h*Qh(t))`
- Difference: `-alpha_3*er(t) + gamma_h*Rh(t) - mu_h*Qh(t) + (delta_r + mu_r)*ir(t) - Derivative(Qh(t), t) + Derivative(ir(t), t)`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(sh(t), t), beta_h - mu_h*sh(t) + phi*qh(t) - (beta_1*ir(t) + beta_2*ih(t))*sh(t)/N_h)`
- Matrix:  `Eq(Derivative(Et(t), t), -Et*(alpha_3 + mu_t) + It*St*beta_2/N_t)`
- Difference: `(-It*N_h*St*beta_2 + N_h*N_t*(Et*(alpha_3 + mu_t) + beta_h - mu_h*sh(t) + phi*qh(t) + Derivative(Et(t), t) - Derivative(sh(t), t)) - N_t*(beta_1*ir(t) + beta_2*ih(t))*sh(t))/(N_h*N_t)`

**Equation 1:**
- Correct: `Eq(Derivative(eh(t), t), -(alpha_1 + alpha_2 + mu_h)*eh(t) + (beta_1*ir(t) + beta_2*ih(t))*sh(t)/N_h)`
- Matrix:  `Eq(Derivative(Eh(t), t), -Eh*(alpha_1 + alpha_2 + mu_h) + alpha_1*(Ih*beta_1 + It)/N_h)`
- Difference: `(N_h*(Eh*(alpha_1 + alpha_2 + mu_h) - (alpha_1 + alpha_2 + mu_h)*eh(t) + Derivative(Eh(t), t) - Derivative(eh(t), t)) - alpha_1*(Ih*beta_1 + It) + (beta_1*ir(t) + beta_2*ih(t))*sh(t))/N_h`

**Equation 2:**
- Correct: `Eq(Derivative(ih(t), t), alpha_1*eh(t) - (delta_h + gamma + mu_h)*ih(t))`
- Matrix:  `Eq(Derivative(It(t), t), Et*alpha_3 - It*mu_t)`
- Difference: `-Et*alpha_3 + It*mu_t + alpha_1*eh(t) - (delta_h + gamma + mu_h)*ih(t) + Derivative(It(t), t) - Derivative(ih(t), t)`

**Equation 3:**
- Correct: `Eq(Derivative(qh(t), t), alpha_2*eh(t) - (delta_h + mu_h + phi + tau)*qh(t))`
- Matrix:  `Eq(Derivative(Ih(t), t), Eh*alpha_2 - Qh*(gamma_h + mu_h + phi))`
- Difference: `-Eh*alpha_2 + Qh*(gamma_h + mu_h + phi) + alpha_2*eh(t) - (delta_h + mu_h + phi + tau)*qh(t) + Derivative(Ih(t), t) - Derivative(qh(t), t)`

**Equation 4:**
- Correct: `Eq(Derivative(rh(t), t), gamma*qh(t) - mu_h*rh(t) + tau*qh(t))`
- Matrix:  `Eq(Derivative(Rt(t), t), Et*alpha_3 - Rt*mu_t)`
- Difference: `-Et*alpha_3 + Rt*mu_t + gamma*qh(t) - mu_h*rh(t) + tau*qh(t) + Derivative(Rt(t), t) - Derivative(rh(t), t)`

**Equation 5:**
- Correct: `Eq(Derivative(sr(t), t), beta_r - mu_r*sr(t) - beta_3*ir(t)*sr(t)/N_r)`
- Matrix:  `Eq(Derivative(Sh(t), t), Qh*phi - Sh*mu_h + (Ih*beta_2 + It*beta_1)/N_h)`
- Difference: `-Ih*beta_2/N_h - It*beta_1/N_h - Qh*phi + Sh*mu_h + beta_r - mu_r*sr(t) + Derivative(Sh(t), t) - Derivative(sr(t), t) - beta_3*ir(t)*sr(t)/N_r`

**Equation 6:**
- Correct: `Eq(Derivative(er(t), t), -(alpha_3 + mu_r)*er(t) + beta_3*ir(t)*sr(t)/N_r)`
- Matrix:  `Eq(Derivative(St(t), t), -It*St*beta_2/N_t + St*mu_t)`
- Difference: `It*St*beta_2/N_t - St*mu_t - alpha_3*er(t) - mu_r*er(t) + Derivative(St(t), t) - Derivative(er(t), t) + beta_3*ir(t)*sr(t)/N_r`

**Equation 7:**
- Correct: `Eq(Derivative(ir(t), t), alpha_3*er(t) - (delta_r + mu_r)*ir(t))`
- Matrix:  `Eq(Derivative(Qh(t), t), -Qh*mu_h + gamma_h*Rh(t))`
- Difference: `Qh*mu_h + alpha_3*er(t) - gamma_h*Rh(t) - (delta_r + mu_r)*ir(t) + Derivative(Qh(t), t) - Derivative(ir(t), t)`

