
# Comparison by Subtraction
## Model: BIOMD0000000983
### Timestamp: 2025-09-08_14-20-46

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(E(t), t), beta*(1 - sigma)*(n*I_r(t) + I_u(t))*S_u(t) - mu*E(t))`
- Extracted: `Eq(Derivative(E(t), t), beta*(1 - sigma)*(Ir(t)*n(t) + Iu(t))*Su(t) - mu*E(t))`
- Difference: `beta*(sigma - 1)*((n*I_r(t) + I_u(t))*S_u(t) - (Ir(t)*n(t) + Iu(t))*Su(t))`

**Equation 1:**
- Correct:   `Eq(Derivative(I_r(t), t), -eta_r*I_r(t) + f*mu*E(t) + lambda_*theta*Q(t))`
- Extracted: `Eq(Derivative(Ir(t), t), -eta_r*Ir(t) + f*mu*E(t) + lambda_*theta*Q(t))`
- Difference: `eta_r*I_r(t) - eta_r*Ir(t) + Derivative(I_r(t), t) - Derivative(Ir(t), t)`

**Equation 2:**
- Correct:   `Eq(Derivative(I_u(t), t), -eta_u*I_u(t) + mu*(1 - f)*E(t))`
- Extracted: `Eq(Derivative(Iu(t), t), -eta_u*Iu(t) + mu*(1 - f)*E(t))`
- Difference: `eta_u*I_u(t) - eta_u*Iu(t) + Derivative(I_u(t), t) - Derivative(Iu(t), t)`

**Equation 3:**
- Correct:   `Eq(Derivative(Q(t), t), beta*sigma*(n*I_r(t) + I_u(t))*S_u(t) - theta*Q(t))`
- Extracted: `Eq(Derivative(Q(t), t), beta*sigma*(Ir(t)*n(t) + Iu(t))*Su(t) - theta*Q(t))`
- Difference: `beta*sigma*(-(n*I_r(t) + I_u(t))*S_u(t) + (Ir(t)*n(t) + Iu(t))*Su(t))`

**Equation 4:**
- Correct:   `Eq(Derivative(R(t), t), eta_r*q*I_r(t) + eta_u*I_u(t))`
- Extracted: `Eq(Derivative(R(t), t), eta_r*q*Ir(t) + eta_u*Iu(t))`
- Difference: `-eta_r*q*I_r(t) + eta_r*q*Ir(t) - eta_u*I_u(t) + eta_u*Iu(t)`

**Equation 5:**
- Correct:   `Eq(Derivative(S_c(t), t), -(1 - m(t))*S_c(t) + S_u(t)*m(t))`
- Extracted: `Eq(Derivative(Sc(t), t), -(1 - m(t))*Sc(t) + Su(t)*m(t))`
- Difference: `-(m(t) - 1)*S_c(t) + (m(t) - 1)*Sc(t) - S_u(t)*m(t) + Su(t)*m(t) + Derivative(S_c(t), t) - Derivative(Sc(t), t)`

**Equation 6:**
- Correct:   `Eq(Derivative(S_u(t), t), -beta*(n*I_r(t) + I_u(t))*S_u(t) + theta*(1 - lambda_)*Q(t) + (1 - m(t))*S_c(t) - S_u(t)*m(t))`
- Extracted: `Eq(Derivative(Su(t), t), -beta*(Ir(t)*n(t) + Iu(t))*Su(t) + theta*(1 - lambda_)*Q(t) + (1 - m(t))*Sc(t) - Su(t)*m(t))`
- Difference: `beta*(n*I_r(t) + I_u(t))*S_u(t) - beta*(Ir(t)*n(t) + Iu(t))*Su(t) + (m(t) - 1)*S_c(t) - (m(t) - 1)*Sc(t) + S_u(t)*m(t) - Su(t)*m(t) + Derivative(S_u(t), t) - Derivative(Su(t), t)`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(E(t), t), beta*(1 - sigma)*(n*I_r(t) + I_u(t))*S_u(t) - mu*E(t))`
- Corrected: `Eq(Derivative(E(t), t), beta*(1 - sigma)*(n*Ir(t) + Iu(t))*Su(t) - mu*E(t))`
- Difference: `beta*(sigma - 1)*((n*I_r(t) + I_u(t))*S_u(t) - (n*Ir(t) + Iu(t))*Su(t))`

**Equation 1:**
- Correct: `Eq(Derivative(I_r(t), t), -eta_r*I_r(t) + f*mu*E(t) + lambda_*theta*Q(t))`
- Corrected: `Eq(Derivative(Ir(t), t), -eta_r*Ir(t) + f*mu*E(t) + lambda_*theta*Q(t))`
- Difference: `eta_r*I_r(t) - eta_r*Ir(t) + Derivative(I_r(t), t) - Derivative(Ir(t), t)`

**Equation 2:**
- Correct: `Eq(Derivative(I_u(t), t), -eta_u*I_u(t) + mu*(1 - f)*E(t))`
- Corrected: `Eq(Derivative(Iu(t), t), -eta_u*Iu(t) + mu*(1 - f)*E(t))`
- Difference: `eta_u*I_u(t) - eta_u*Iu(t) + Derivative(I_u(t), t) - Derivative(Iu(t), t)`

**Equation 3:**
- Correct: `Eq(Derivative(Q(t), t), beta*sigma*(n*I_r(t) + I_u(t))*S_u(t) - theta*Q(t))`
- Corrected: `Eq(Derivative(Q(t), t), beta*sigma*(n*Ir(t) + Iu(t))*Su(t) - theta*Q(t))`
- Difference: `beta*sigma*(-(n*I_r(t) + I_u(t))*S_u(t) + (n*Ir(t) + Iu(t))*Su(t))`

**Equation 4:**
- Correct: `Eq(Derivative(R(t), t), eta_r*q*I_r(t) + eta_u*I_u(t))`
- Corrected: `Eq(Derivative(R(t), t), eta_r*q*Ir(t) + eta_u*Iu(t))`
- Difference: `-eta_r*q*I_r(t) + eta_r*q*Ir(t) - eta_u*I_u(t) + eta_u*Iu(t)`

**Equation 5:**
- Correct: `Eq(Derivative(S_c(t), t), -(1 - m(t))*S_c(t) + S_u(t)*m(t))`
- Corrected: `Eq(Derivative(Sc(t), t), m*Su(t) - (1 - m)*Sc(t))`
- Difference: `m*Su(t) + (m - 1)*Sc(t) - (m(t) - 1)*S_c(t) - S_u(t)*m(t) + Derivative(S_c(t), t) - Derivative(Sc(t), t)`

**Equation 6:**
- Correct: `Eq(Derivative(S_u(t), t), -beta*(n*I_r(t) + I_u(t))*S_u(t) + theta*(1 - lambda_)*Q(t) + (1 - m(t))*S_c(t) - S_u(t)*m(t))`
- Corrected: `Eq(Derivative(Su(t), t), -beta*(n*Ir(t) + Iu(t))*Su(t) - m*Su(t) + theta*(1 - lambda_)*Q(t) + (1 - m)*Sc(t))`
- Difference: `beta*(n*I_r(t) + I_u(t))*S_u(t) - beta*(n*Ir(t) + Iu(t))*Su(t) - m*Su(t) - (m - 1)*Sc(t) + (m(t) - 1)*S_c(t) + S_u(t)*m(t) + Derivative(S_u(t), t) - Derivative(Su(t), t)`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(E(t), t), beta*(1 - sigma)*(n*I_r(t) + I_u(t))*S_u(t) - mu*E(t))`
- Matrix:  `Eq(Derivative(E(t), t), Su*beta*(1 - sigma)*(Ir*n + Iu) - mu*E(t))`
- Difference: `beta*(sigma - 1)*(Su*(Ir*n + Iu) - (n*I_r(t) + I_u(t))*S_u(t))`

**Equation 1:**
- Correct: `Eq(Derivative(I_r(t), t), -eta_r*I_r(t) + f*mu*E(t) + lambda_*theta*Q(t))`
- Matrix:  `Eq(Derivative(Ir(t), t), -Ir*eta_r + Q*lambda_*theta + f*mu*E(t))`
- Difference: `Ir*eta_r - Q*lambda_*theta - eta_r*I_r(t) + lambda_*theta*Q(t) - Derivative(I_r(t), t) + Derivative(Ir(t), t)`

**Equation 2:**
- Correct: `Eq(Derivative(I_u(t), t), -eta_u*I_u(t) + mu*(1 - f)*E(t))`
- Matrix:  `Eq(Derivative(Iu(t), t), -Iu*eta_u + mu*(1 - f)*E(t))`
- Difference: `Iu*eta_u - eta_u*I_u(t) - Derivative(I_u(t), t) + Derivative(Iu(t), t)`

**Equation 3:**
- Correct: `Eq(Derivative(Q(t), t), beta*sigma*(n*I_r(t) + I_u(t))*S_u(t) - theta*Q(t))`
- Matrix:  `Eq(Derivative(Q(t), t), -Q*lambda_*theta - Q*theta*(1 - lambda_) + Su*beta*sigma*(Ir*n + Iu))`
- Difference: `Q*lambda_*theta - Q*theta*(lambda_ - 1) - Su*beta*sigma*(Ir*n + Iu) + beta*sigma*(n*I_r(t) + I_u(t))*S_u(t) - theta*Q(t)`

**Equation 4:**
- Correct: `Eq(Derivative(R(t), t), eta_r*q*I_r(t) + eta_u*I_u(t))`
- Matrix:  `Eq(Derivative(R(t), t), Ir*eta_r*q + Iu*eta_u)`
- Difference: `-Ir*eta_r*q - Iu*eta_u + eta_r*q*I_r(t) + eta_u*I_u(t)`

**Equation 5:**
- Correct: `Eq(Derivative(S_c(t), t), -(1 - m(t))*S_c(t) + S_u(t)*m(t))`
- Matrix:  `Eq(Derivative(Su(t), t), Q*theta*(1 - lambda_) + Sc*(1 - m) - Su*beta*(Ir*n + Iu) - Su*m)`
- Difference: `Q*theta*(lambda_ - 1) + Sc*(m - 1) + Su*beta*(Ir*n + Iu) + Su*m + (m(t) - 1)*S_c(t) + S_u(t)*m(t) - Derivative(S_c(t), t) + Derivative(Su(t), t)`

**Equation 6:**
- Correct: `Eq(Derivative(S_u(t), t), -beta*(n*I_r(t) + I_u(t))*S_u(t) + theta*(1 - lambda_)*Q(t) + (1 - m(t))*S_c(t) - S_u(t)*m(t))`
- Matrix:  `Eq(Derivative(Sc(t), t), -Sc*(1 - m) + Su*m)`
- Difference: `-Sc*(m - 1) - Su*m - beta*(n*I_r(t) + I_u(t))*S_u(t) - theta*(lambda_ - 1)*Q(t) - (m(t) - 1)*S_c(t) - S_u(t)*m(t) - Derivative(S_u(t), t) + Derivative(Sc(t), t)`

