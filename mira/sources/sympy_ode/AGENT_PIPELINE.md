# MIRA Equation Extraction Workflow

This document outlines the implementation of mathematical equation extraction from
articles in the MIRA framework.

---

## Key Files
- Process: `mira/notebooks/llm_extraction.ipynb`
- Pipeline: `mira/sources/sympy_ode/agent_pipeliene.py`
- Core functions: `mira/sources/sympy_ode/llm_util.py`
- Prompts: `mira/sources/sympy_ode/constants.py`

Detailed results can be found in: `mira/notebooks/mira_llm_extraction_evaluation.ipynb`

---

## Multi-Agent Pipeline

There are clearly separable problem areas, which are better managed by breaking
down the agent architecture into more steps.

A multi-agent-based approach systematically addresses extraction challenges by
organizing the process into distinct phases, each targeting specific aspects:

### Phase 1: ODE Extraction
- Done by `ODEExtractionSpecialist`
- Extraction is integrated into the pipeline to ensure conservation of all
  information during the initial first step

### Phase 2: Concept Grounding
- Done by `ConceptGrounder`
- Regular expression pattern matching to extract ODE definitions
- Semantic analysis of variable names and contexts
- Generation of `concept_data` dictionary with biological/epidemiological
  annotations

### Phase 3: Execution Error Correction
- Done by `ExecutionErrorCorrector`
- Iterative workflow for finding and correcting execution errors
- Automated fixes for:
  - Missing imports (sympy modules)
  - Undefined symbols/functions
  - Namespace conflicts
  - Syntax errors

### Post-Pipeline Processing

After the pipeline completes, the system creates a **TemplateModel** using the
validated ODEs and grounded concepts.

This pipeline transforms the single-shot extraction into a robust, multi-step
process where each agent specializes in one aspect of validation and correction.

Since each agent requires a distinct approach and prompt configuration, the LLM
can achieve better focus (rather than receiving a summarized, less detailed
message).

## Future Possible Phases

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
- Quantitative measures are implemented to replace manual ODE comparison, 
  providing automated accuracy assessment

### Other Possible Validation Checks
1. **Symbol Validation** - Are all variables and parameters defined? (focuses 
   more on JSON)
2. **Biological Context Tagging** - Are compartments semantically labeled 
   (e.g., S = susceptible)?
3. **JSON Structure Integrity** - Is the output JSON consistent and complete?

---

## Other Future Directions

- **Initial conditions extraction:** Automatically identify and extract initial 
  values for state variables from source documents
- **Parameter information extraction:** Mine the full article for parameter 
  values, units, and contextual descriptions
- **Scaling the method:** Extend the pipeline to handle larger document sets 
  and batch processing of multiple biomodels
