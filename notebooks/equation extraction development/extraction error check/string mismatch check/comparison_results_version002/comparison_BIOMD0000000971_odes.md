
# Comparison by Subtraction
## Model: BIOMD0000000971
### Timestamp: 2025-09-08_13-33-58

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(A(t), t), -gamma_A*A(t) + sigma*(1 - rho)*E(t))`
- Extracted: `Eq(Derivative(A(t), t), -gamma_A*A(t) + sigma*(1 - q)*E(t))`
- Difference: `sigma*(-q + rho)*E(t)`

**Equation 1:**
- Correct:   `Eq(Derivative(E(t), t), beta*c*(1 - q)*(theta*A(t) + I(t))*S(t) - sigma*E(t))`
- Extracted: `Eq(Derivative(E(t), t), beta*c*(1 - q)*(theta*A(t) + I(t))*S(t) - sigma*E(t))`
- Difference: `0`

**Equation 2:**
- Correct:   `Eq(Derivative(E_q(t), t), beta*c*q*(theta*A(t) + I(t))*S(t) - delta_q*E_q(t))`
- Extracted: `Eq(Derivative(Eq(t), t), beta*c*q*(theta*A(t) + I(t))*S(t) - delta_q*Eq(t))`
- Difference: `delta_q*E_q(t) - delta_q*Eq(t) + Derivative(E_q(t), t) - Derivative(Eq(t), t)`

**Equation 3:**
- Correct:   `Eq(Derivative(H(t), t), delta_I*I(t) + delta_q*E_q(t) - (alpha + gamma_H)*H(t))`
- Extracted: `Eq(Derivative(H(t), t), delta_I*I(t) + delta_q*Eq(t) - (alpha + gamma_H)*H(t))`
- Difference: `delta_q*(-E_q(t) + Eq(t))`

**Equation 4:**
- Correct:   `Eq(Derivative(I(t), t), rho*sigma*E(t) - (alpha + delta_I + gamma_I)*I(t))`
- Extracted: `Eq(Derivative(I(t), t), q*sigma*E(t) - (alpha + delta_I + gamma_I)*I(t))`
- Difference: `sigma*(q - rho)*E(t)`

**Equation 5:**
- Correct:   `Eq(Derivative(R(t), t), gamma_A*A(t) + gamma_H*H(t) + gamma_I*I(t))`
- Extracted: `Eq(Derivative(R(t), t), gamma_A*A(t) + gamma_H*H(t) + gamma_I*I(t))`
- Difference: `0`

**Equation 6:**
- Correct:   `Eq(Derivative(S(t), t), lambda_*S_q(t) + (-beta*c - c*q*(1 - beta))*(theta*A(t) + I(t))*S(t))`
- Extracted: `Eq(Derivative(S(t), t), lambda_*Sq(t) + (-beta*c - q*(1 - beta))*(theta*A(t) + I(t))*S(t))`
- Difference: `c*(beta - q*(beta - 1))*(theta*A(t) + I(t))*S(t) - lambda_*S_q(t) + lambda_*Sq(t) - (beta*c - q*(beta - 1))*(theta*A(t) + I(t))*S(t)`

**Equation 7:**
- Correct:   `Eq(Derivative(S_q(t), t), c*q*(1 - beta)*(theta*A(t) + I(t))*S(t) - lambda_*S_q(t))`
- Extracted: `Eq(Derivative(Sq(t), t), c*q*(1 - beta)*(theta*A(t) + I(t))*S(t) - lambda_*Sq(t))`
- Difference: `lambda_*S_q(t) - lambda_*Sq(t) + Derivative(S_q(t), t) - Derivative(Sq(t), t)`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(A(t), t), -gamma_A*A(t) + sigma*(1 - rho)*E(t))`
- Corrected: `Eq(Derivative(A(t), t), -gamma_A*A(t) + sigma*(1 - q)*E(t))`
- Difference: `sigma*(-q + rho)*E(t)`

**Equation 1:**
- Correct: `Eq(Derivative(E(t), t), beta*c*(1 - q)*(theta*A(t) + I(t))*S(t) - sigma*E(t))`
- Corrected: `Eq(Derivative(E(t), t), beta*c*(1 - q)*(theta*A(t) + I(t))*S(t) - sigma*E(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(E_q(t), t), beta*c*q*(theta*A(t) + I(t))*S(t) - delta_q*E_q(t))`
- Corrected: `Eq(Derivative(Eq(t), t), beta*c*q*(theta*A(t) + I(t))*S(t) - delta_q*Eq(t))`
- Difference: `delta_q*E_q(t) - delta_q*Eq(t) + Derivative(E_q(t), t) - Derivative(Eq(t), t)`

**Equation 3:**
- Correct: `Eq(Derivative(H(t), t), delta_I*I(t) + delta_q*E_q(t) - (alpha + gamma_H)*H(t))`
- Corrected: `Eq(Derivative(H(t), t), delta_I*I(t) + delta_q*Eq(t) - (alpha + gamma_H)*H(t))`
- Difference: `delta_q*(-E_q(t) + Eq(t))`

**Equation 4:**
- Correct: `Eq(Derivative(I(t), t), rho*sigma*E(t) - (alpha + delta_I + gamma_I)*I(t))`
- Corrected: `Eq(Derivative(I(t), t), q*sigma*E(t) - (alpha + delta_I + gamma_I)*I(t))`
- Difference: `sigma*(q - rho)*E(t)`

**Equation 5:**
- Correct: `Eq(Derivative(R(t), t), gamma_A*A(t) + gamma_H*H(t) + gamma_I*I(t))`
- Corrected: `Eq(Derivative(R(t), t), gamma_A*A(t) + gamma_H*H(t) + gamma_I*I(t))`
- Difference: `0`

**Equation 6:**
- Correct: `Eq(Derivative(S(t), t), lambda_*S_q(t) + (-beta*c - c*q*(1 - beta))*(theta*A(t) + I(t))*S(t))`
- Corrected: `Eq(Derivative(S(t), t), lambda_*Sq(t) + (-beta*c - q*(1 - beta))*(theta*A(t) + I(t))*S(t))`
- Difference: `c*(beta - q*(beta - 1))*(theta*A(t) + I(t))*S(t) - lambda_*S_q(t) + lambda_*Sq(t) - (beta*c - q*(beta - 1))*(theta*A(t) + I(t))*S(t)`

**Equation 7:**
- Correct: `Eq(Derivative(S_q(t), t), c*q*(1 - beta)*(theta*A(t) + I(t))*S(t) - lambda_*S_q(t))`
- Corrected: `Eq(Derivative(Sq(t), t), c*q*(1 - beta)*(theta*A(t) + I(t))*S(t) - lambda_*Sq(t))`
- Difference: `lambda_*S_q(t) - lambda_*Sq(t) + Derivative(S_q(t), t) - Derivative(Sq(t), t)`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(A(t), t), -gamma_A*A(t) + sigma*(1 - rho)*E(t))`
- Matrix:  `Eq(Derivative(A(t), t), -gamma_A*A(t) + sigma*(1 - q)*E(t))`
- Difference: `sigma*(q - rho)*E(t)`

**Equation 1:**
- Correct: `Eq(Derivative(E(t), t), beta*c*(1 - q)*(theta*A(t) + I(t))*S(t) - sigma*E(t))`
- Matrix:  `Eq(Derivative(E(t), t), beta*c*(1 - q)*(theta*A(t) + I(t))*S(t) - q*sigma*E(t) - sigma*(1 - q)*E(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(E_q(t), t), beta*c*q*(theta*A(t) + I(t))*S(t) - delta_q*E_q(t))`
- Matrix:  `Eq(Derivative(Eq(t), t), -Eq*delta_q + beta*c*q*(theta*A(t) + I(t))*S(t))`
- Difference: `Eq*delta_q - delta_q*E_q(t) - Derivative(E_q(t), t) + Derivative(Eq(t), t)`

**Equation 3:**
- Correct: `Eq(Derivative(H(t), t), delta_I*I(t) + delta_q*E_q(t) - (alpha + gamma_H)*H(t))`
- Matrix:  `Eq(Derivative(H(t), t), Eq*delta_q + delta_I*I(t) - (alpha + gamma_H)*H(t))`
- Difference: `delta_q*(-Eq + E_q(t))`

**Equation 4:**
- Correct: `Eq(Derivative(I(t), t), rho*sigma*E(t) - (alpha + delta_I + gamma_I)*I(t))`
- Matrix:  `Eq(Derivative(I(t), t), q*sigma*E(t) - (alpha + delta_I + gamma_I)*I(t))`
- Difference: `sigma*(-q + rho)*E(t)`

**Equation 5:**
- Correct: `Eq(Derivative(R(t), t), gamma_A*A(t) + gamma_H*H(t) + gamma_I*I(t))`
- Matrix:  `Eq(Derivative(R(t), t), gamma_A*A(t) + gamma_H*H(t) + gamma_I*I(t))`
- Difference: `0`

**Equation 6:**
- Correct: `Eq(Derivative(S(t), t), lambda_*S_q(t) + (-beta*c - c*q*(1 - beta))*(theta*A(t) + I(t))*S(t))`
- Matrix:  `Eq(Derivative(S(t), t), Sq*lambda + (-beta*c - q*(1 - beta))*(theta*A(t) + I(t))*S(t))`
- Difference: `-Sq*lambda - c*(beta - q*(beta - 1))*(theta*A(t) + I(t))*S(t) + lambda_*S_q(t) + (beta*c - q*(beta - 1))*(theta*A(t) + I(t))*S(t)`

**Equation 7:**
- Correct: `Eq(Derivative(S_q(t), t), c*q*(1 - beta)*(theta*A(t) + I(t))*S(t) - lambda_*S_q(t))`
- Matrix:  `Eq(Derivative(Sq(t), t), -Sq*lambda + c*q*(1 - beta)*(theta*A(t) + I(t))*S(t))`
- Difference: `Sq*lambda - lambda_*S_q(t) - Derivative(S_q(t), t) + Derivative(Sq(t), t)`

