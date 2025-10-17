# MIRA Equation Extraction Workflow

This document outlines the evolution and implementation of mathematical equation extraction from PDFs in the MIRA framework.

---

## Version 001: One-shot Prompting

The basic workflow of MIRA uses a one-shot prompting architecture.

**Key Files:**
- Process: `mira/notebooks/llm_extraction.ipynb`
- Pipeline: `mira/sources/sympy_ode/llm_util.py`
- Prompts: `mira/sources/sympy_ode/constants.py`

Detailed results can be found in: `mira_llm_extraction_evaluation.ipynb`

---

## Version 002: Iterative Prompting Workflow

To improve extraction precision, an iterative workflow was introduced with a two-agent system:

### Agent 1: Extraction Agent
First, an extraction agent uses the original MIRA process to convert equation images into SymPy code and ground biological concepts.

### Agent 2: Validation Agent
Then, a validation agent checks the extraction for:
- Execution errors (missing imports, undefined variables)
- Parameter consistency issues
- Incorrect concept grounding

If errors are found, the validation agent corrects them and the process repeats for up to 3 iterations until all checks pass.

This multi-agent approach improves extraction accuracy by catching and fixing common errors that the single-shot method might miss, while maintaining backward compatibility with the existing MIRA codebase.

### Implementation Results

**Repository:** `fruzsedua/mira/tree/extraction-development`

**Examples:** `mira/notebooks/equation extraction development/extraction error check/string mismatch check/comparison_results_version002`

**Key Files:**
- Process: `mira/notebooks/llm_extraction.ipynb` (more detailed process)
- Pipeline: `mira/sources/sympy_ode/llm_util.py` (new functions added)
- Prompts: `mira/sources/sympy_ode/constants.py` (error handling prompt added)

### Image Extraction Improvements
- Additional rules added: symmetry, transmission structure, patterns, mathematical structure, parameter consistency, completeness check
- Epidemiology-based rules are just ideas (from Claude) → **revision needed!**

### Error Checking and Correcting
**Execution errors** are mostly fixed during iteration 1:
- Syntax rules for detecting and handling functions/symbols
- Handling of imports, utilizing their names precisely
- Missing parameters are included

**Other improvements:**
- Data parsing alignment between prompt output format and next function
- Comparing number of factors to the original (count * operators and variables)
- Preserving content between iterations of the error handling prompt
- Missing `/N` fixed

### Comparison of Extracted ODEs
- Sympy format matching
- Sorting of equations (based on the variable on the LHS) for comparison
- Template Model → Mtx odes confuses information due to multiple formatting steps → **fix needed!**

### Pipeline Integration

Error handling multi-agent architecture is part of the template model creation pipeline:

**Image → LLM Extraction → Multi-Agent Validation → JSON (corrected ODEs + concepts) → Template Model → Mtx odes**

### Remaining Errors
- **Parameter consistency:** mostly symbolic differences (e.g. `rho_1` vs. `rho1`), sometimes more serious: e.g. `rho` vs. `q` (similar) → LLM has no info which one is used, doesn't know it needs fix
- **Multiplication vs. addition** still gets mixed up sometimes
- **Semantic compartment mismatches** `I(t)` vs. `T(t)` → extra validation needed
- **Arithmetic validation** strengthening is much needed!
- **Precision of coefficient extraction**
- **Still remains:** `CodeExecutionError: Error while executing the code: 'Symbol' object is not callable` (examples: BIOMD000000972, BIOMD000000976)
- **The error handling function** mixes up the order of operations in some cases (example: BIOMD0000000991)
- **Extraction of compartments** differ from the original completely, maybe derived from the RHS (example: 2024_dec_epi_1_model_A)

---

## Version 003: Multi-Agent Pipeline (Current)

There are clearly separable problem areas, which are better managed by breaking down the agent architecture into more steps.

A multi-agent-based approach systematically addresses extraction challenges by organizing the process into distinct phases, each targeting specific aspects:

### Phase 1: ODE Extraction (`ODEExtractionSpecialist`)
- Initial extraction as in version 001
- Extraction is integrated into the pipeline to ensure conservation of all information during the initial first step

### Phase 2: Concept Grounding (`ConceptGrounder`)
- Regular expression pattern matching to extract ODE definitions
- Semantic analysis of variable names and contexts
- Generation of `concept_data` dictionary with biological/epidemiological annotations (same as version 001)

### Phase 3: Execution Error Correction (`ExecutionErrorCorrector`)
- Iterative workflow for finding and correcting execution errors
- Automated fixes for:
  - Missing imports (sympy modules)
  - Undefined symbols/functions
  - Namespace conflicts
  - Syntax errors

### Phase 4: Dual Validation (`ValidationAggregator` + `MathematicalAggregator`)

**ValidationAggregator:**
- Parameter consistency checking
- Time-dependency classification
- Symbol usage validation

**MathematicalAggregator:**
- Dimensional analysis
- Conservation law verification
- Mathematical structure validation

### Phase 5: Unified Error Correction (`UnifiedErrorCorrector`)
- Comprehensive error analysis from all previous phases
- Prioritized correction strategy
- Fixes for:
  - Symbol/Function type mismatches
  - Missing transmission terms (e.g., `/N`)
  - Parameter definition inconsistencies
  - Equation completeness issues

### Phase 6: Quantitative Evaluation (`QuantitativeEvaluator`)
- Load correct equations from manually pre-made TSV file
- String normalization and comparison
- Calculation of metrics:
  - **Execution Success Rate:** Binary pass/fail
  - **Equation Accuracy Rate:** Percentage of matching equations
  - **Detailed comparison:** Per-equation match status
- **Quantitative measures are implemented to replace manual ODE comparison, providing automated accuracy assessment**

### Post-Pipeline Processing

After the pipeline completes, the system creates a **TemplateModel** using the validated ODEs and grounded concepts.

This pipeline transforms the single-shot extraction into a robust, multi-step process where each agent specializes in one aspect of validation and correction.

Since each agent requires a distinct approach and prompt configuration, the LLM can achieve better focus (rather than receiving a summarized, less detailed message).

### Other Possible Agenda Items

6. **Symbol Validation** – Are all variables and parameters defined? (focuses more on JSON)
7. **Biological Context Tagging** – Are compartments semantically labeled (e.g., S = susceptible)?
8. **JSON Structure Integrity** – Is the output JSON consistent and complete?

---

## Next Steps

- **Initial conditions extraction:** Automatically identify and extract initial values for state variables from source documents
- **Parameter information extraction:** Mine the full article for parameter values, units, and contextual descriptions
- **Scaling the method:** Extend the pipeline to handle larger document sets and batch processing of multiple biomodels