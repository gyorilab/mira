
# Comparison by Subtraction
## Model: BIOMD0000000963
### Timestamp: 2025-09-08_12-51-56

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(I(t), t), beta*I(t)*S(t)/(alpha*R(t) + 1) - gamma*I(t))`
- Extracted: `Eq(Derivative(I(t), t), beta*I(t)*S(t)/(alpha*R(t) + 1) - gamma*I(t))`
- Difference: `0`

**Equation 1:**
- Correct:   `Eq(Derivative(R(t), t), gamma*I(t))`
- Extracted: `Eq(Derivative(R(t), t), gamma*I(t))`
- Difference: `0`

**Equation 2:**
- Correct:   `Eq(Derivative(S(t), t), -beta*I(t)*S(t)/(alpha*R(t) + 1))`
- Extracted: `Eq(Derivative(S(t), t), -beta*I(t)*S(t)/(alpha*R(t) + 1))`
- Difference: `0`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(I(t), t), beta*I(t)*S(t)/(alpha*R(t) + 1) - gamma*I(t))`
- Corrected: `Eq(Derivative(I(t), t), beta*I(t)*S(t)/(alpha*R(t) + 1) - gamma*I(t))`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(R(t), t), gamma*I(t))`
- Corrected: `Eq(Derivative(R(t), t), gamma*I(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(S(t), t), -beta*I(t)*S(t)/(alpha*R(t) + 1))`
- Corrected: `Eq(Derivative(S(t), t), -beta*I(t)*S(t)/(alpha*R(t) + 1))`
- Difference: `0`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(I(t), t), beta*I(t)*S(t)/(alpha*R(t) + 1) - gamma*I(t))`
- Matrix:  `Eq(Derivative(I(t), t), beta*I(t)*S(t)/(alpha*R(t) + 1) - gamma*I(t))`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(R(t), t), gamma*I(t))`
- Matrix:  `Eq(Derivative(R(t), t), gamma*I(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(S(t), t), -beta*I(t)*S(t)/(alpha*R(t) + 1))`
- Matrix:  `Eq(Derivative(S(t), t), -beta*I(t)*S(t)/(alpha*R(t) + 1))`
- Difference: `0`

