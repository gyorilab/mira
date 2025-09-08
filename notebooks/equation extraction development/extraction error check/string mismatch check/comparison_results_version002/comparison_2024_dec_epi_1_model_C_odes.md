
# Comparison by Subtraction
## Model: 2024_dec_epi_1_model_C
### Timestamp: 2025-09-08_15-03-44

## 1. correct_odes vs extracted_odes_sympy

**Equation 0:**
- Correct:   `Eq(Derivative(s_m(t), t), -lambda_m*s_m(t))`
- Extracted: `Eq(Derivative(s_m(t), t), -lambda_m*s_m(t))`
- Difference: `0`

**Equation 1:**
- Correct:   `Eq(Derivative(e_m(t), t), -alpha_m*e_m(t) + lambda_m*s_m(t))`
- Extracted: `Eq(Derivative(e_m(t), t), -alpha_m*e_m(t) + lambda_m*s_m(t))`
- Difference: `0`

**Equation 2:**
- Correct:   `Eq(Derivative(i_m(t), t), alpha_m*e_m(t) - tau_m*i_m(t))`
- Extracted: `Eq(Derivative(i_m(t), t), alpha_m*e_m(t) - tau_m*i_m(t))`
- Difference: `0`

**Equation 3:**
- Correct:   `Eq(Derivative(r_m(t), t), tau_m*i_m(t))`
- Extracted: `Eq(Derivative(r_m(t), t), tau_m*i_m(t))`
- Difference: `0`

**Equation 4:**
- Correct:   `Eq(Derivative(s_w(t), t), -lambda_w*s_w(t))`
- Extracted: `Eq(Derivative(s_w(t), t), -lambda_w*s_w(t))`
- Difference: `0`

**Equation 5:**
- Correct:   `Eq(Derivative(e_w(t), t), -alpha_w*e_w(t) + lambda_w*s_w(t))`
- Extracted: `Eq(Derivative(e_w(t), t), -alpha_w*e_w(t) + lambda_w*s_w(t))`
- Difference: `0`

**Equation 6:**
- Correct:   `Eq(Derivative(i_w(t), t), alpha_w*e_w(t) - tau_w*i_w(t))`
- Extracted: `Eq(Derivative(i_w(t), t), alpha_w*e_w(t) - tau_w*i_w(t))`
- Difference: `0`

**Equation 7:**
- Correct:   `Eq(Derivative(r_w(t), t), tau_w*i_w(t))`
- Extracted: `Eq(Derivative(r_w(t), t), tau_w*i_w(t))`
- Difference: `0`

## 2. correct_odes vs corrected_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(s_m(t), t), -lambda_m*s_m(t))`
- Corrected: `Eq(Derivative(s_m(t), t), -lambda_m*s_m(t))`
- Difference: `0`

**Equation 1:**
- Correct: `Eq(Derivative(e_m(t), t), -alpha_m*e_m(t) + lambda_m*s_m(t))`
- Corrected: `Eq(Derivative(e_m(t), t), -alpha_m*e_m(t) + lambda_m*s_m(t))`
- Difference: `0`

**Equation 2:**
- Correct: `Eq(Derivative(i_m(t), t), alpha_m*e_m(t) - tau_m*i_m(t))`
- Corrected: `Eq(Derivative(i_m(t), t), alpha_m*e_m(t) - tau_m*i_m(t))`
- Difference: `0`

**Equation 3:**
- Correct: `Eq(Derivative(r_m(t), t), tau_m*i_m(t))`
- Corrected: `Eq(Derivative(r_m(t), t), tau_m*i_m(t))`
- Difference: `0`

**Equation 4:**
- Correct: `Eq(Derivative(s_w(t), t), -lambda_w*s_w(t))`
- Corrected: `Eq(Derivative(s_w(t), t), -lambda_w*s_w(t))`
- Difference: `0`

**Equation 5:**
- Correct: `Eq(Derivative(e_w(t), t), -alpha_w*e_w(t) + lambda_w*s_w(t))`
- Corrected: `Eq(Derivative(e_w(t), t), -alpha_w*e_w(t) + lambda_w*s_w(t))`
- Difference: `0`

**Equation 6:**
- Correct: `Eq(Derivative(i_w(t), t), alpha_w*e_w(t) - tau_w*i_w(t))`
- Corrected: `Eq(Derivative(i_w(t), t), alpha_w*e_w(t) - tau_w*i_w(t))`
- Difference: `0`

**Equation 7:**
- Correct: `Eq(Derivative(r_w(t), t), tau_w*i_w(t))`
- Corrected: `Eq(Derivative(r_w(t), t), tau_w*i_w(t))`
- Difference: `0`

## 3. correct_odes vs mtx_odes_sympy

**Equation 0:**
- Correct: `Eq(Derivative(s_m(t), t), -lambda_m*s_m(t))`
- Matrix:  `Eq(Derivative(s_m(t), t), -lambda_m*s_m)`
- Difference: `lambda_m*(s_m - s_m(t))`

**Equation 1:**
- Correct: `Eq(Derivative(e_m(t), t), -alpha_m*e_m(t) + lambda_m*s_m(t))`
- Matrix:  `Eq(Derivative(e_m(t), t), -alpha_m*e_m + lambda_m*s_m)`
- Difference: `alpha_m*e_m - alpha_m*e_m(t) - lambda_m*s_m + lambda_m*s_m(t)`

**Equation 2:**
- Correct: `Eq(Derivative(i_m(t), t), alpha_m*e_m(t) - tau_m*i_m(t))`
- Matrix:  `Eq(Derivative(i_m(t), t), alpha_m*e_m - i_m*tau_m)`
- Difference: `-alpha_m*e_m + alpha_m*e_m(t) + i_m*tau_m - tau_m*i_m(t)`

**Equation 3:**
- Correct: `Eq(Derivative(r_m(t), t), tau_m*i_m(t))`
- Matrix:  `Eq(Derivative(r_m(t), t), i_m*tau_m)`
- Difference: `tau_m*(-i_m + i_m(t))`

**Equation 4:**
- Correct: `Eq(Derivative(s_w(t), t), -lambda_w*s_w(t))`
- Matrix:  `Eq(Derivative(s_w(t), t), -lambda_w*s_w)`
- Difference: `lambda_w*(s_w - s_w(t))`

**Equation 5:**
- Correct: `Eq(Derivative(e_w(t), t), -alpha_w*e_w(t) + lambda_w*s_w(t))`
- Matrix:  `Eq(Derivative(e_w(t), t), -alpha_w*e_w + lambda_w*s_w)`
- Difference: `alpha_w*e_w - alpha_w*e_w(t) - lambda_w*s_w + lambda_w*s_w(t)`

**Equation 6:**
- Correct: `Eq(Derivative(i_w(t), t), alpha_w*e_w(t) - tau_w*i_w(t))`
- Matrix:  `Eq(Derivative(i_w(t), t), alpha_w*e_w - i_w*tau_w)`
- Difference: `-alpha_w*e_w + alpha_w*e_w(t) + i_w*tau_w - tau_w*i_w(t)`

**Equation 7:**
- Correct: `Eq(Derivative(r_w(t), t), tau_w*i_w(t))`
- Matrix:  `Eq(Derivative(r_w(t), t), i_w*tau_w)`
- Difference: `tau_w*(-i_w + i_w(t))`

