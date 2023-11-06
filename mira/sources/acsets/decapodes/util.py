PARTIAL_TIME_DERIVATIVE = "∂ₜ"
BINARY_OPERATIONS = {"Mult"}  # todo: extend
FUNCTION_NAME_MAPPING = {"♯": 'Sharp',
                         '⋆₁': 'dot_subscript_1',
                         '∂ₜ': "d_subscript_t",
                         '⋆₀⁻¹': 'dot_subscript_o_superscript_-1'}
INVERSE_FUNCTION_NAME_MAPPING = {v: k for k, v in FUNCTION_NAME_MAPPING.items()}
