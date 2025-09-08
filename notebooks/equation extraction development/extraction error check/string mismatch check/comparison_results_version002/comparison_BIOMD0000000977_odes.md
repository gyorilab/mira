
# Comparison by Subtraction
## Model: BIOMD0000000977
### Timestamp: 2025-09-08_14-07-41

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(A(t), t), -(delta + gamma_a + xi_a)*A(t) + beta_s*epsilon_s*(1 - rho_s)*I(t)*S(t)/N)`
- Extracted: `Eq(Derivative(A(t), t), -(delta + gamma_a + xi_a)*A(t) + beta_s*epsilon_s*(1 - rho_s)*I(t)*S(t)/N)`
- Difference: `0`

**Equation 1:**
- Correct:   `Eq(Derivative(I(t), t), gamma_a*A(t) - (delta + gamma_i + xi_i)*I(t))`
- Extracted: `Eq(Derivative(I(t), t), gamma_a*A(t) - (delta + gamma_i + xi_i)*I(t))`
- Difference: `0`

**Equation 2:**
- Correct:   `Eq(Derivative(I_q(t), t), gamma_i*I(t) - (delta + xi_q)*I_q(t) + beta_s*epsilon_s*rho_s*I(t)*S(t)/N)`
- Extracted: `Eq(Derivative(Iq(t), t), gamma_i*I(t) - (delta + xi_q)*Iq(t) + beta_s*epsilon_s*rho_s*I(t)*S(t)/N)`
- Difference: `(delta + xi_q)*I_q(t) - (delta + xi_q)*Iq(t) + Derivative(I_q(t), t) - Derivative(Iq(t), t)`

**Equation 3:**
- Correct:   `Eq(Derivative(R(t), t), -delta*R(t) + xi_a*A(t) + xi_i*I(t) + xi_q*I_q(t))`
- Extracted: `Eq(Derivative(R(t), t), -delta*R(t) + xi_a*A(t) + xi_i*I(t) + xi_q*Iq(t))`
- Difference: `xi_q*(-I_q(t) + Iq(t))`

**Equation 4:**
- Correct:   `Eq(Derivative(S(t), t), Lambda_s - delta*S(t) + m_s*S_q(t) - epsilon_s*(beta_s + rho_s*(1 - beta_s))*I(t)*S(t)/N)`
- Extracted: `Eq(Derivative(S(t), t), Lambda_s - delta*S(t) + m_s*S_q(t) - epsilon_s*(beta_s + rho_s*(1 - beta_s))*I(t)*S(t)/N)`
- Difference: `0`

**Equation 5:**
- Correct:   `Eq(Derivative(S_q(t), t), -(delta + m_s)*S_q(t) + epsilon_s*rho_s*(1 - beta_s)*I(t)*S(t)/N)`
- Extracted: `Eq(Derivative(Sq(t), t), -(delta + m_s)*Sq(t) + epsilon_s*rho_s*(1 - beta_s)*I(t)*S(t)/N)`
- Difference: `(delta + m_s)*S_q(t) - (delta + m_s)*Sq(t) + Derivative(S_q(t), t) - Derivative(Sq(t), t)`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(A(t), t), -(delta + gamma_a + xi_a)*A(t) + beta_s*epsilon_s*(1 - rho_s)*I(t)*S(t)/N)`
- Corrected: `Eq(Derivative(A(t), t), -(delta + gamma_a + xi_a)*A(t) + beta_s*epsilon_s*(1 - rho_s)*I(t)*S(t)/N)`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(I(t), t), gamma_a*A(t) - (delta + gamma_i + xi_i)*I(t))`
- Corrected: `Eq(Derivative(I(t), t), gamma_a*A(t) - (delta + xi_i + gamma_i(t))*I(t))`
- Difference: `(gamma_i - gamma_i(t))*I(t)`

**Equation 2:**
- Correct: `Eq(Derivative(I_q(t), t), gamma_i*I(t) - (delta + xi_q)*I_q(t) + beta_s*epsilon_s*rho_s*I(t)*S(t)/N)`
- Corrected: `Eq(Derivative(Iq(t), t), -(delta + xi_q)*Iq(t) + I(t)*gamma_i(t) + beta_s*epsilon_s*rho_s*I(t)*S(t)/N)`
- Difference: `-gamma_i*I(t) + (delta + xi_q)*I_q(t) - (delta + xi_q)*Iq(t) + I(t)*gamma_i(t) + Derivative(I_q(t), t) - Derivative(Iq(t), t)`

**Equation 3:**
- Correct: `Eq(Derivative(R(t), t), -delta*R(t) + xi_a*A(t) + xi_i*I(t) + xi_q*I_q(t))`
- Corrected: `Eq(Derivative(R(t), t), -delta*R(t) + xi_a*A(t) + xi_i*I(t) + xi_q*Iq(t))`
- Difference: `xi_q*(-I_q(t) + Iq(t))`

**Equation 4:**
- Correct: `Eq(Derivative(S(t), t), Lambda_s - delta*S(t) + m_s*S_q(t) - epsilon_s*(beta_s + rho_s*(1 - beta_s))*I(t)*S(t)/N)`
- Corrected: `Eq(Derivative(S(t), t), Lambda_s - delta*S(t) + m_s*Sq(t) - epsilon_s*(beta_s + rho_s*(1 - beta_s))*I(t)*S(t)/N)`
- Difference: `m_s*(-S_q(t) + Sq(t))`

**Equation 5:**
- Correct: `Eq(Derivative(S_q(t), t), -(delta + m_s)*S_q(t) + epsilon_s*rho_s*(1 - beta_s)*I(t)*S(t)/N)`
- Corrected: `Eq(Derivative(Sq(t), t), -(delta + m_s)*Sq(t) + epsilon_s*rho_s*(1 - beta_s)*I(t)*S(t)/N)`
- Difference: `(delta + m_s)*S_q(t) - (delta + m_s)*Sq(t) + Derivative(S_q(t), t) - Derivative(Sq(t), t)`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(A(t), t), -(delta + gamma_a + xi_a)*A(t) + beta_s*epsilon_s*(1 - rho_s)*I(t)*S(t)/N)`
- Matrix:  `Eq(Derivative(A(t), t), -(delta + gamma_a + xi_a)*A(t) + beta_s*epsilon_s*(1 - rho_s)*I(t)*S(t)/N)`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(I(t), t), gamma_a*A(t) - (delta + gamma_i + xi_i)*I(t))`
- Matrix:  `Eq(Derivative(I(t), t), gamma_a*A(t) - (delta + xi_i + gamma_i(t))*I(t))`
- Difference: `(-gamma_i + gamma_i(t))*I(t)`

**Equation 2:**
- Correct: `Eq(Derivative(I_q(t), t), gamma_i*I(t) - (delta + xi_q)*I_q(t) + beta_s*epsilon_s*rho_s*I(t)*S(t)/N)`
- Matrix:  `Eq(Derivative(Iq(t), t), -Iq*(delta + xi_q) + I(t)*gamma_i(t) + beta_s*epsilon_s*rho_s*I(t)*S(t)/N)`
- Difference: `Iq*(delta + xi_q) + gamma_i*I(t) - (delta + xi_q)*I_q(t) - I(t)*gamma_i(t) - Derivative(I_q(t), t) + Derivative(Iq(t), t)`

**Equation 3:**
- Correct: `Eq(Derivative(R(t), t), -delta*R(t) + xi_a*A(t) + xi_i*I(t) + xi_q*I_q(t))`
- Matrix:  `Eq(Derivative(R(t), t), Iq*xi_q - delta*R(t) + xi_a*A(t) + xi_i*I(t))`
- Difference: `xi_q*(-Iq + I_q(t))`

**Equation 4:**
- Correct: `Eq(Derivative(S(t), t), Lambda_s - delta*S(t) + m_s*S_q(t) - epsilon_s*(beta_s + rho_s*(1 - beta_s))*I(t)*S(t)/N)`
- Matrix:  `Eq(Derivative(S(t), t), Lambda_s + Sq*m_s - delta*S(t) - epsilon_s*(beta_s + rho_s*(1 - beta_s))*I(t)*S(t)/N)`
- Difference: `m_s*(-Sq + S_q(t))`

**Equation 5:**
- Correct: `Eq(Derivative(S_q(t), t), -(delta + m_s)*S_q(t) + epsilon_s*rho_s*(1 - beta_s)*I(t)*S(t)/N)`
- Matrix:  `Eq(Derivative(Sq(t), t), -Sq*(delta + m_s) + epsilon_s*rho_s*(1 - beta_s)*I(t)*S(t)/N)`
- Difference: `Sq*(delta + m_s) - (delta + m_s)*S_q(t) - Derivative(S_q(t), t) + Derivative(Sq(t), t)`

