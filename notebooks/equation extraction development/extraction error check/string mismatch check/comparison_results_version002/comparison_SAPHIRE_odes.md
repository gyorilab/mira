
# Comparison by Subtraction
## Model: SAPHIRE
### Timestamp: 2025-09-08_14-52-40

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(A(t), t), -n*A(t)/N + (1 - r)*P(t)/Dp - A(t)/Di)`
- Extracted: `Eq(Derivative(A(t), t), -n*A(t)/N + (1 - r)*P(t)/Dp - A(t)/Di)`
- Difference: `0`

**Equation 1:**
- Correct:   `Eq(Derivative(E(t), t), b*(alpha*A(t) + alpha*P(t) + l)*S(t)/N - n*E(t)/N - E(t)/De)`
- Extracted: `Eq(Derivative(E(t), t), b*(alpha*A(t) + alpha*P(t) + l)*S(t)/N - n*E(t)/N - E(t)/De)`
- Difference: `0`

**Equation 2:**
- Correct:   `Eq(Derivative(H(t), t), I(t)/Dq - H(t)/Dh)`
- Extracted: `Eq(Derivative(H(t), t), I(t)/Dq - H(t)/Dh)`
- Difference: `0`

**Equation 3:**
- Correct:   `Eq(Derivative(I(t), t), -I(t)/Dq + r*P(t)/Dp - I(t)/Di)`
- Extracted: `Eq(Derivative(I(t), t), -I(t)/Dq + r*P(t)/Dp - I(t)/Di)`
- Difference: `0`

**Equation 4:**
- Correct:   `Eq(Derivative(P(t), t), -n*P(t)/N - P(t)/Dp + E(t)/De)`
- Extracted: `Eq(Derivative(P(t), t), -n*P(t)/N - P(t)/Dp + E(t)/De)`
- Difference: `0`

**Equation 5:**
- Correct:   `Eq(Derivative(R(t), t), A(t) - n*R(t)/N + I(t)/Di - H(t)/Dh)`
- Extracted: `Eq(Derivative(R(t), t), -n*R(t)/N + A(t)/Di + H(t)/Dh)`
- Difference: `-A(t) + A(t)/Di - I(t)/Di + 2*H(t)/Dh`

**Equation 6:**
- Correct:   `Eq(Derivative(S(t), t), n - b*(alpha*A(t) + alpha*P(t) + l)*S(t)/N - n*S(t)/N)`
- Extracted: `Eq(Derivative(S(t), t), n - b*(alpha*A(t) + alpha*P(t) + l)*S(t)/N - n*S(t)/N)`
- Difference: `0`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(A(t), t), -n*A(t)/N + (1 - r)*P(t)/Dp - A(t)/Di)`
- Corrected: `Eq(0, n - S*b*(A*alpha + P*alpha + l)/N - S*n/N)`
- Difference: `(Di*Dp*N*(n + Derivative(A(t), t)) + Di*Dp*(-S*b*(A*alpha + P*alpha + l) - S*n + n*A(t)) + Di*N*(r - 1)*P(t) + Dp*N*A(t))/(Di*Dp*N)`

**Equation 1:**
- Correct: `Eq(Derivative(E(t), t), b*(alpha*A(t) + alpha*P(t) + l)*S(t)/N - n*E(t)/N - E(t)/De)`
- Corrected: `Eq(0, -E*n/N + S*b*(A*alpha + P*alpha + l)/N - E/De)`
- Difference: `(De*N*Derivative(E(t), t) + De*(-E*n + S*b*(A*alpha + P*alpha + l) - b*(alpha*A(t) + alpha*P(t) + l)*S(t) + n*E(t)) + N*(-E + E(t)))/(De*N)`

**Equation 2:**
- Correct: `Eq(Derivative(H(t), t), I(t)/Dq - H(t)/Dh)`
- Corrected: `Eq(0, -P*n/N - P/Dp + E/De)`
- Difference: `Derivative(H(t), t) - P*n/N - I(t)/Dq - P/Dp + H(t)/Dh + E/De`

**Equation 3:**
- Correct: `Eq(Derivative(I(t), t), -I(t)/Dq + r*P(t)/Dp - I(t)/Di)`
- Corrected: `Eq(0, -A*n/N - A/Di + P*(1 - r)/Dp)`
- Difference: `-A*n/N - A/Di + Derivative(I(t), t) + I(t)/Dq - P*r/Dp + P/Dp - r*P(t)/Dp + I(t)/Di`

**Equation 4:**
- Correct: `Eq(Derivative(P(t), t), -n*P(t)/N - P(t)/Dp + E(t)/De)`
- Corrected: `Eq(0, -I/Dq + P*r/Dp - I/Di)`
- Difference: `Derivative(P(t), t) + n*P(t)/N - I/Dq + P*r/Dp + P(t)/Dp - I/Di - E(t)/De`

**Equation 5:**
- Correct: `Eq(Derivative(R(t), t), A(t) - n*R(t)/N + I(t)/Di - H(t)/Dh)`
- Corrected: `Eq(0, I/Dq - H/Dh)`
- Difference: `-A(t) + Derivative(R(t), t) + n*R(t)/N + I/Dq - I(t)/Di - H/Dh + H(t)/Dh`

**Equation 6:**
- Correct: `Eq(Derivative(S(t), t), n - b*(alpha*A(t) + alpha*P(t) + l)*S(t)/N - n*S(t)/N)`
- Corrected: `Eq(0, A/Di - R*n/N + H/Dh)`
- Difference: `(A*Dh*N + Dh*Di*N*(-n + Derivative(S(t), t)) + Dh*Di*(-R*n + b*(alpha*A(t) + alpha*P(t) + l)*S(t) + n*S(t)) + Di*H*N)/(Dh*Di*N)`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(A(t), t), -n*A(t)/N + (1 - r)*P(t)/Dp - A(t)/Di)`
- Matrix:  `Eq(Derivative(A(t), t), -n*A(t)/N + (1 - r)*P(t)/Dp - A(t)/Di)`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(E(t), t), b*(alpha*A(t) + alpha*P(t) + l)*S(t)/N - n*E(t)/N - E(t)/De)`
- Matrix:  `Eq(Derivative(E(t), t), b*(alpha*A(t) + alpha*P(t) + l)*S(t)/N - n*E(t)/N - E(t)/De)`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(H(t), t), I(t)/Dq - H(t)/Dh)`
- Matrix:  `Eq(Derivative(H(t), t), I(t)/Dq - H(t)/Dh)`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(I(t), t), -I(t)/Dq + r*P(t)/Dp - I(t)/Di)`
- Matrix:  `Eq(Derivative(I(t), t), -I(t)/Dq + r*P(t)/Dp - I(t)/Di)`
- Difference: `0`

**Equation 4:**
- Correct: `Eq(Derivative(P(t), t), -n*P(t)/N - P(t)/Dp + E(t)/De)`
- Matrix:  `Eq(Derivative(P(t), t), -n*P(t)/N - r*P(t)/Dp - (1 - r)*P(t)/Dp + E(t)/De)`
- Difference: `0`

**Equation 5:**
- Correct: `Eq(Derivative(R(t), t), A(t) - n*R(t)/N + I(t)/Di - H(t)/Dh)`
- Matrix:  `Eq(Derivative(R(t), t), -n*R(t)/N + A(t)/Di + H(t)/Dh)`
- Difference: `A(t) - A(t)/Di + I(t)/Di - 2*H(t)/Dh`

**Equation 6:**
- Correct: `Eq(Derivative(S(t), t), n - b*(alpha*A(t) + alpha*P(t) + l)*S(t)/N - n*S(t)/N)`
- Matrix:  `Eq(Derivative(S(t), t), n - b*(alpha*A(t) + alpha*P(t) + l)*S(t)/N - n*S(t)/N)`
- Difference: `0`

