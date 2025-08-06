# Advanced Prompting Strategy for Equation Extraction in MIRA

## Executive Summary

This document outlines an advanced prompting strategy for extracting mathematical equations from PDFs using OpenAI's models, specifically designed for the MIRA (Machine-assisted Modeling of Dynamical Systems) framework. The approach incorporates cutting-edge computer science methodologies from recent research in LLM-based equation discovery.

## Theoretical Foundation

### 1. LLM-SR Framework (Scientific Equation Discovery via Programming)

**Core Concept**: Treat equations as programs with mathematical operators and combine LLMs' scientific priors with evolutionary search over equation programs.

**Implementation**: 
- Use structured prompts that leverage the LLM's embedded scientific knowledge
- Implement iterative hypothesis generation and refinement
- Apply evolutionary optimization principles to improve extraction quality

### 2. Multi-Modal Document Understanding

**Advanced Method**: Combine text extraction with visual understanding of mathematical notation, figures, and equation layouts in PDFs.

**Benefits**:
- Better recognition of complex mathematical symbols
- Understanding of equation context from surrounding figures
- Preservation of spatial relationships in mathematical expressions

### 3. Chain-of-Thought Mathematical Reasoning

**Approach**: Employ explicit code-based self-verification to boost mathematical reasoning potential by having the LLM verify its extracted equations through computational methods.

## Proposed Agenda and Implementation

### Phase 1: Evaluation (Baseline Extraction)

**Objective**: Establish baseline extraction performance and identify target equations.

**Prompting Strategy**:
```
SYSTEM: You are an expert mathematical equation extractor specializing in 
dynamical systems and epidemiological models. Focus on identifying:
1. Differential equations (ODEs and PDEs)
2. Compartmental model equations  
3. Rate equations and kinetic expressions
4. Parameter definitions and constraints

USER: Extract all mathematical equations from this text, providing:
- LaTeX representation
- Variables and parameters
- Equation classification
- Confidence score (0-1)
- Surrounding context

TEXT: [document_content]
```

**Advanced Features**:
- Multi-pass extraction with different focus areas
- Confidence scoring for each extraction
- Context preservation for better understanding

### Phase 2: Time Dependency Analysis

**Objective**: Identify temporal relationships and dynamic behavior in extracted equations.

**Methodology**: 
- Analyze differential operators and time derivatives
- Identify state variables vs. parameters
- Detect time scales (fast/slow dynamics)
- Map temporal dependencies between variables

**Prompting Strategy**:
```
Analyze this equation for temporal behavior:
Equation: {latex}
Variables: {variables}

Identify:
1. Time-dependent variables (explicit ∂/∂t, implicit dynamics)
2. Time scales (characteristic times, separation of scales)
3. Initial conditions required
4. Equilibrium points and stability
5. Causal relationships between variables

Focus on epidemiological and biological time dependencies.
```

### Phase 3: Missing Values and Parameter Detection

**Objective**: Ensure completeness of extracted mathematical models.

**Advanced Validation Approach**:
- Cross-reference parameters across multiple equations
- Identify implicit assumptions and hidden parameters
- Detect dimensional inconsistencies
- Validate biological/physical plausibility

**Prompting Strategy**:
```
Validate equation completeness:
Equation: {latex}
Context: {surrounding_text}

Check for:
1. Missing rate constants or parameters
2. Undefined variables or symbols
3. Implicit assumptions (e.g., constant population, homogeneous mixing)
4. Dimensional consistency
5. Biological constraints (positivity, conservation laws)

Suggest missing components with scientific justification.
```

### Phase 4: Template Matching (TM) for MIRA Integration

**Objective**: Map extracted equations to MIRA's template system for seamless integration.

**Template Categories**:
- SIR/SEIR epidemiological models
- Lotka-Volterra predator-prey systems
- Chemical reaction networks
- Population dynamics models
- Stochastic differential equations

**Matching Algorithm**:
1. **Structural Similarity**: Compare equation form and operators
2. **Variable Correspondence**: Match variable names and roles
3. **Parameter Alignment**: Identify corresponding parameters
4. **Biological Meaning**: Ensure semantic consistency

**Advanced Prompting for Template Matching**:
```
Map this equation to standard mathematical biology templates:

Equation: {latex}
Variables: {variables}
Parameters: {parameters}

Compare against:
1. SIR/SEIR compartmental models
2. Lotka-Volterra dynamics
3. Chemical kinetics (mass action, Michaelis-Menten)
4. Population growth models (logistic, exponential)
5. Stochastic processes (birth-death, diffusion)

Provide:
- Best template match with similarity score
- Variable/parameter mapping
- Required transformations or extensions
- MIRA template format conversion
```

## Advanced Computer Science Methodologies

### 1. Evolutionary Equation Optimization

**Inspired by**: LLM-SR's combination of LLM scientific priors with evolutionary search

**Implementation**:
- Generate multiple equation hypotheses per extracted candidate
- Use fitness functions based on mathematical consistency
- Apply mutation and crossover operations on equation structures
- Select best equations based on multiple criteria

### 2. Self-Reflective Improvement Loop

**Method**: Implement iterative refinement where the LLM critiques and improves its own extractions.

**Process**:
1. Initial extraction
2. Self-evaluation and issue identification
3. Targeted improvement prompts
4. Validation and re-extraction if needed

### 3. Multi-Agent Collaboration

**Approach**: Use specialized "agent" prompts for different aspects:
- **Extraction Agent**: Focuses on finding equations
- **Validation Agent**: Checks mathematical correctness
- **Biology Agent**: Ensures biological plausibility
- **Integration Agent**: Maps to MIRA templates

### 4. Semantic Parsing with Mathematical Expression Trees

**Advanced Feature**: Convert extracted LaTeX to structured representations for better analysis.

**Benefits**:
- Enable programmatic manipulation of equations
- Facilitate template matching algorithms
- Support automated parameter sensitivity analysis

## Quality Assurance and Evaluation

### Evaluation Metrics

1. **Extraction Completeness**: Percentage of equations found vs. manually identified
2. **Accuracy**: Correctness of LaTeX representation
3. **Parameter Completeness**: Fraction of parameters correctly identified
4. **Template Matching Success**: Accuracy of MIRA template assignments
5. **Biological Plausibility**: Expert evaluation of extracted model validity

### Validation Pipeline

```python
def evaluate_extraction_quality(extracted_equations, ground_truth):
    """
    Comprehensive evaluation of extraction quality
    """
    metrics = {
        'precision': compute_precision(extracted_equations, ground_truth),
        'recall': compute_recall(extracted_equations, ground_truth),
        'f1_score': compute_f1_score(extracted_equations, ground_truth),
        'parameter_accuracy': evaluate_parameter_extraction(extracted_equations, ground_truth),
        'template_matching_accuracy': evaluate_template_matching(extracted_equations, ground_truth),
        'biological_validity': expert_validation_score(extracted_equations)
    }
    return metrics
```

## Recommended Implementation Sequence

### Phase 1: Foundation (Weeks 1-2)
- Implement basic PDF extraction and OpenAI integration
- Develop initial prompting strategies
- Create evaluation framework

### Phase 2: Core Algorithms (Weeks 3-4)
- Implement temporal dependency analysis
- Develop parameter validation system
- Create template matching algorithms

### Phase 3: Advanced Features (Weeks 5-6)
- Add iterative self-improvement
- Implement multi-agent collaboration
- Integrate with MIRA system

### Phase 4: Optimization (Weeks 7-8)
- Performance tuning and optimization
- Comprehensive testing and validation
- Documentation and user interface development

## Integration with MIRA Ecosystem

### Template Format Conversion

The extracted equations should be converted to MIRA's template format:

```python
def convert_to_mira_template(equation: ExtractedEquation) -> Dict:
    """
    Convert extracted equation to MIRA template format
    """
    template = {
        "template_type": equation.equation_type.value,
        "rate_law": equation.latex,
        "subject": identify_subject_variable(equation),
        "outcome": identify_outcome_variable(equation),
        "controllers": equation.parameters,
        "context": {
            "temporal_dependencies": equation.temporal_dependencies,
            "missing_parameters": equation.missing_parameters
        }
    }
    return template
```

### Knowledge Graph Integration

Leverage MIRA's knowledge graph capabilities by:
- Mapping extracted parameters to ontological concepts
- Linking equations to biological processes
- Enabling semantic queries over extracted models

## Future Directions

### 1. Multi-Modal Enhancement
- Direct image processing of mathematical figures
- Understanding of diagram-equation relationships
- Visual equation verification

### 2. Active Learning
- Iterative improvement based on user feedback
- Adaptive prompting strategies
- Continuous model refinement

### 3. Domain Specialization
- Epidemiology-specific extraction patterns
- Pharmacokinetics model recognition
- Systems biology pathway extraction

## Conclusion

This advanced prompting strategy combines state-of-the-art LLM capabilities with domain-specific knowledge to create a robust equation extraction system for the MIRA framework. The multi-phase approach ensures comprehensive extraction while maintaining high accuracy and biological relevance.

The suggested agenda of **Evaluation → Time Dependency → Missing Parameters → Template Matching** provides a logical progression that builds understanding incrementally and ensures robust integration with the MIRA ecosystem.
