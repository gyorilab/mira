
# Comparison by Subtraction
## Model: BIOMD0000000955
### Timestamp: 2025-09-08_11-36-20

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(A(t), t), zeta*I(t) - (kappa + mu + theta)*A(t))`
- Extracted: `Eq(Derivative(A(t), t), zeta*I(t) - (kappa + mu + theta)*A(t))`
- Difference: `0`

**Equation 1:**
- Correct:   `Eq(Derivative(D(t), t), epsilon*I(t) - (eta + rho)*D(t))`
- Extracted: `Eq(Derivative(D(t), t), epsilon*I(t) - eta*D(t))`
- Difference: `rho*D(t)`

**Equation 2:**
- Correct:   `Eq(Derivative(E(t), t), tau*T(t))`
- Extracted: `Eq(Derivative(E(t), t), tau*T(t))`
- Difference: `0`

**Equation 3:**
- Correct:   `Eq(Derivative(H(t), t), kappa*A(t) + lambda_*I(t) + rho*D(t) + sigma*T(t) + xi*R(t))`
- Extracted: `Eq(Derivative(H(t), t), kappa*A(t) + lambda_*I(t) + rho*D(t) + sigma*T(t) + xi*R(t))`
- Difference: `0`

**Equation 4:**
- Correct:   `Eq(Derivative(I(t), t), -(epsilon + lambda_ + zeta)*I(t) + (alpha*I(t) + beta*D(t) + delta*R(t) + gamma*A(t))*S(t))`
- Extracted: `Eq(Derivative(I(t), t), -(epsilon + lambda_ + zeta)*I(t) + (alpha*I(t) + beta*D(t) + delta*R(t) + gamma*A(t))*S(t))`
- Difference: `0`

**Equation 5:**
- Correct:   `Eq(Derivative(R(t), t), eta*D(t) + theta*A(t) - (nu + xi)*R(t))`
- Extracted: `Eq(Derivative(R(t), t), eta*D(t) + theta*A(t) - (nu + xi)*R(t))`
- Difference: `0`

**Equation 6:**
- Correct:   `Eq(Derivative(S(t), t), -(alpha*I(t) + beta*D(t) + delta*R(t) + gamma*A(t))*S(t))`
- Extracted: `Eq(Derivative(S(t), t), -(alpha*I(t) + beta*D(t) + delta*R(t) + gamma*A(t))*S(t))`
- Difference: `0`

**Equation 7:**
- Correct:   `Eq(Derivative(T(t), t), mu*A(t) + nu*R(t) - (sigma + tau)*T(t))`
- Extracted: `Eq(Derivative(T(t), t), mu*A(t) + nu*R(t) - (sigma + tau)*T(t))`
- Difference: `0`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(A(t), t), zeta*I(t) - (kappa + mu + theta)*A(t))`
- Corrected: `Eq(Derivative(A(t), t), zeta*I(t) - (kappa + mu + theta)*A(t))`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(D(t), t), epsilon*I(t) - (eta + rho)*D(t))`
- Corrected: `Eq(Derivative(D(t), t), epsilon*I(t) - eta*D(t))`
- Difference: `rho*D(t)`

**Equation 2:**
- Correct: `Eq(Derivative(E(t), t), tau*T(t))`
- Corrected: `Eq(Derivative(E(t), t), tau*T(t))`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(H(t), t), kappa*A(t) + lambda_*I(t) + rho*D(t) + sigma*T(t) + xi*R(t))`
- Corrected: `Eq(Derivative(H(t), t), kappa*A(t) + lambda_*I(t) + rho*D(t) + sigma*T(t) + xi*R(t))`
- Difference: `0`

**Equation 4:**
- Correct: `Eq(Derivative(I(t), t), -(epsilon + lambda_ + zeta)*I(t) + (alpha*I(t) + beta*D(t) + delta*R(t) + gamma*A(t))*S(t))`
- Corrected: `Eq(Derivative(I(t), t), -(epsilon + lambda_ + zeta)*I(t) + (alpha*I(t) + beta*D(t) + delta*R(t) + gamma*A(t))*S(t))`
- Difference: `0`

**Equation 5:**
- Correct: `Eq(Derivative(R(t), t), eta*D(t) + theta*A(t) - (nu + xi)*R(t))`
- Corrected: `Eq(Derivative(R(t), t), eta*D(t) + theta*A(t) - (nu + xi)*R(t))`
- Difference: `0`

**Equation 6:**
- Correct: `Eq(Derivative(S(t), t), -(alpha*I(t) + beta*D(t) + delta*R(t) + gamma*A(t))*S(t))`
- Corrected: `Eq(Derivative(S(t), t), -(alpha*I(t) + beta*D(t) + delta*R(t) + gamma*A(t))*S(t))`
- Difference: `0`

**Equation 7:**
- Correct: `Eq(Derivative(T(t), t), mu*A(t) + nu*R(t) - (sigma + tau)*T(t))`
- Corrected: `Eq(Derivative(T(t), t), mu*A(t) + nu*R(t) - (sigma + tau)*T(t))`
- Difference: `0`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(A(t), t), zeta*I(t) - (kappa + mu + theta)*A(t))`
- Matrix:  `Eq(Derivative(A(t), t), zeta*I(t) - (kappa + mu + theta)*A(t))`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(D(t), t), epsilon*I(t) - (eta + rho)*D(t))`
- Matrix:  `Eq(Derivative(D(t), t), -D*eta + epsilon*I(t))`
- Difference: `D*eta - (eta + rho)*D(t)`

**Equation 2:**
- Correct: `Eq(Derivative(E(t), t), tau*T(t))`
- Matrix:  `Eq(Derivative(E(t), t), T*tau)`
- Difference: `tau*(-T + T(t))`

**Equation 3:**
- Correct: `Eq(Derivative(H(t), t), kappa*A(t) + lambda_*I(t) + rho*D(t) + sigma*T(t) + xi*R(t))`
- Matrix:  `Eq(Derivative(H(t), t), D*rho + T*sigma + kappa*A(t) + lambda*I(t) + xi*R(t))`
- Difference: `-D*rho - T*sigma - lambda*I(t) + lambda_*I(t) + rho*D(t) + sigma*T(t)`

**Equation 4:**
- Correct: `Eq(Derivative(I(t), t), -(epsilon + lambda_ + zeta)*I(t) + (alpha*I(t) + beta*D(t) + delta*R(t) + gamma*A(t))*S(t))`
- Matrix:  `Eq(Derivative(I(t), t), -(epsilon + lambda + zeta)*I(t) + (D*beta + alpha*I(t) + delta*R(t) + gamma*A(t))*S(t))`
- Difference: `-D*beta*S(t) + beta*D(t)*S(t) + lambda*I(t) - lambda_*I(t)`

**Equation 5:**
- Correct: `Eq(Derivative(R(t), t), eta*D(t) + theta*A(t) - (nu + xi)*R(t))`
- Matrix:  `Eq(Derivative(R(t), t), D*eta + theta*A(t) - (nu + xi)*R(t))`
- Difference: `eta*(-D + D(t))`

**Equation 6:**
- Correct: `Eq(Derivative(S(t), t), -(alpha*I(t) + beta*D(t) + delta*R(t) + gamma*A(t))*S(t))`
- Matrix:  `Eq(Derivative(S(t), t), -(D*beta + alpha*I(t) + delta*R(t) + gamma*A(t))*S(t))`
- Difference: `beta*(D - D(t))*S(t)`

**Equation 7:**
- Correct: `Eq(Derivative(T(t), t), mu*A(t) + nu*R(t) - (sigma + tau)*T(t))`
- Matrix:  `Eq(Derivative(T(t), t), -T*sigma - T*tau + mu*A(t) + nu*R(t))`
- Difference: `T*sigma + T*tau - (sigma + tau)*T(t)`

