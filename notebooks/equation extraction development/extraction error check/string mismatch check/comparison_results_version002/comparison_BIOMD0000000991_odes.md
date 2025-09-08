
# Comparison by Subtraction
## Model: BIOMD0000000991
### Timestamp: 2025-09-08_14-41-44

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(A(t), t), nu*sigma*E(t) - (gamma_a + theta)*A(t))`
- Extracted: `Eq(Derivative(A(t), t), nu*sigma*E(t) - (gamma_a + theta)*A(t))`
- Difference: `0`

**Equation 1:**
- Correct:   `Eq(Derivative(E(t), t), beta_c*(alpha*A(t) + I(t))*S(t)/(N_h - I_D(t)) - sigma*E(t))`
- Extracted: `Eq(Derivative(E(t), t), beta_c*(alpha*A(t) + I(t))*S(t)/(-I_D + N_h) - sigma*E(t))`
- Difference: `beta_c*(-I_D + I_D(t))*(alpha*A(t) + I(t))*S(t)/((I_D - N_h)*(N_h - I_D(t)))`

**Equation 2:**
- Correct:   `Eq(Derivative(I(t), t), sigma*(1 - nu)*E(t) - (d_O + gamma_O + psi)*I(t))`
- Extracted: `Eq(Derivative(I(t), t), sigma*(1 - nu)*E(t) - (d_O + gamma_O + psi)*I(t))`
- Difference: `0`

**Equation 3:**
- Correct:   `Eq(Derivative(I_D(t), t), psi*I(t) + theta*A(t) - (d_D + gamma_i)*I_D(t))`
- Extracted: `Eq(Derivative(ID(t), t), psi*I(t) + theta*A(t) - (d_D + gamma_i)*ID(t))`
- Difference: `-(d_D + gamma_i)*ID(t) + (d_D + gamma_i)*I_D(t) - Derivative(ID(t), t) + Derivative(I_D(t), t)`

**Equation 4:**
- Correct:   `Eq(Derivative(R(t), t), gamma_O*I(t) + gamma_a*A(t) + gamma_i*I_D(t))`
- Extracted: `Eq(Derivative(R(t), t), gamma_O*I(t) + gamma_a*A(t) + gamma_i*ID(t))`
- Difference: `gamma_i*(ID(t) - I_D(t))`

**Equation 5:**
- Correct:   `Eq(Derivative(S(t), t), -beta_c*(alpha*A(t) + I(t))*S(t)/(N_h - I_D(t)))`
- Extracted: `Eq(Derivative(S(t), t), -beta_c*(alpha*A(t) + I(t))*S(t)/(-I_D + N_h))`
- Difference: `beta_c*(I_D - I_D(t))*(alpha*A(t) + I(t))*S(t)/((I_D - N_h)*(N_h - I_D(t)))`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(A(t), t), nu*sigma*E(t) - (gamma_a + theta)*A(t))`
- Corrected: `Eq(Derivative(A(t), t), nu*sigma*E(t) - (gamma_a + theta)*A(t))`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(E(t), t), beta_c*(alpha*A(t) + I(t))*S(t)/(N_h - I_D(t)) - sigma*E(t))`
- Corrected: `Eq(Derivative(E(t), t), beta_c*(alpha*A(t) + I(t))*S(t)/(-I_D + N_h) - sigma*E(t))`
- Difference: `beta_c*(-I_D + I_D(t))*(alpha*A(t) + I(t))*S(t)/((I_D - N_h)*(N_h - I_D(t)))`

**Equation 2:**
- Correct: `Eq(Derivative(I(t), t), sigma*(1 - nu)*E(t) - (d_O + gamma_O + psi)*I(t))`
- Corrected: `Eq(Derivative(I(t), t), sigma*(1 - nu)*E(t) - (d_O + gamma_O + psi)*I(t))`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(I_D(t), t), psi*I(t) + theta*A(t) - (d_D + gamma_i)*I_D(t))`
- Corrected: `Eq(Derivative(ID(t), t), psi*I(t) + theta*A(t) - (d_D + gamma_i)*ID(t))`
- Difference: `-(d_D + gamma_i)*ID(t) + (d_D + gamma_i)*I_D(t) - Derivative(ID(t), t) + Derivative(I_D(t), t)`

**Equation 4:**
- Correct: `Eq(Derivative(R(t), t), gamma_O*I(t) + gamma_a*A(t) + gamma_i*I_D(t))`
- Corrected: `Eq(Derivative(R(t), t), gamma_O*I(t) + gamma_a*A(t) + gamma_i*ID(t))`
- Difference: `gamma_i*(ID(t) - I_D(t))`

**Equation 5:**
- Correct: `Eq(Derivative(S(t), t), -beta_c*(alpha*A(t) + I(t))*S(t)/(N_h - I_D(t)))`
- Corrected: `Eq(Derivative(S(t), t), -beta_c*(alpha*A(t) + I(t))*S(t)/(-I_D + N_h))`
- Difference: `beta_c*(I_D - I_D(t))*(alpha*A(t) + I(t))*S(t)/((I_D - N_h)*(N_h - I_D(t)))`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(A(t), t), nu*sigma*E(t) - (gamma_a + theta)*A(t))`
- Matrix:  `Eq(Derivative(A(t), t), nu*sigma*E(t) - (gamma_a + theta)*A(t))`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(E(t), t), beta_c*(alpha*A(t) + I(t))*S(t)/(N_h - I_D(t)) - sigma*E(t))`
- Matrix:  `Eq(Derivative(E(t), t), beta_c*(alpha*A(t) + I(t))*S(t)/(-I_D + N_h) - nu*sigma*E(t) - sigma*(1 - nu)*E(t))`
- Difference: `beta_c*(I_D - I_D(t))*(alpha*A(t) + I(t))*S(t)/((I_D - N_h)*(N_h - I_D(t)))`

**Equation 2:**
- Correct: `Eq(Derivative(I(t), t), sigma*(1 - nu)*E(t) - (d_O + gamma_O + psi)*I(t))`
- Matrix:  `Eq(Derivative(ID(t), t), -ID*(d_D + gamma_i) + psi*I(t) + theta*A(t))`
- Difference: `ID*(d_D + gamma_i) - psi*I(t) - sigma*(nu - 1)*E(t) - theta*A(t) - (d_O + gamma_O + psi)*I(t) - Derivative(I(t), t) + Derivative(ID(t), t)`

**Equation 3:**
- Correct: `Eq(Derivative(I_D(t), t), psi*I(t) + theta*A(t) - (d_D + gamma_i)*I_D(t))`
- Matrix:  `Eq(Derivative(I(t), t), sigma*(1 - nu)*E(t) - (d_O + gamma_O + psi)*I(t))`
- Difference: `psi*I(t) + sigma*(nu - 1)*E(t) + theta*A(t) - (d_D + gamma_i)*I_D(t) + (d_O + gamma_O + psi)*I(t) + Derivative(I(t), t) - Derivative(I_D(t), t)`

**Equation 4:**
- Correct: `Eq(Derivative(R(t), t), gamma_O*I(t) + gamma_a*A(t) + gamma_i*I_D(t))`
- Matrix:  `Eq(Derivative(R(t), t), ID*gamma_i + gamma_O*I(t) + gamma_a*A(t))`
- Difference: `gamma_i*(-ID + I_D(t))`

**Equation 5:**
- Correct: `Eq(Derivative(S(t), t), -beta_c*(alpha*A(t) + I(t))*S(t)/(N_h - I_D(t)))`
- Matrix:  `Eq(Derivative(S(t), t), -beta_c*(alpha*A(t) + I(t))*S(t)/(-I_D + N_h))`
- Difference: `beta_c*(-I_D + I_D(t))*(alpha*A(t) + I(t))*S(t)/((I_D - N_h)*(N_h - I_D(t)))`

