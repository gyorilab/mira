# agents.py
import json
import sympy
from typing import Dict, Tuple, Optional, List
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """Base class for all agents"""
    
    def __init__(self, client):
        self.client = client
        self.name = self.__class__.__name__
    
    @abstractmethod
    def process(self, input_data: Dict) -> Dict:
        pass

# PHASE 1: EXTRACTION
class ODEExtractionSpecialist(BaseAgent):
    """Phase 1: Extract ODEs from image"""
    
    def process(self, input_data: Dict) -> Dict:
        image_path = input_data['image_path']
        # Use existing extraction logic
        from mira.sources.sympy_ode.llm_util import image_file_to_odes_str
        ode_str = image_file_to_odes_str(image_path, self.client)
        
        return {
            'ode_str': ode_str,
            'phase': 'extraction',
            'status': 'complete'
        }

# PHASE 2: EXECUTION ERROR CHECK & CORRECTION
class ExecutionErrorCorrector(BaseAgent):
    """Phase 2: Check and fix execution errors immediately"""
    
    def process(self, input_data: Dict) -> Dict:
        ode_str = input_data['ode_str']
        
        prompt = """
You are an execution error specialist. Fix ONLY execution errors.

Code to fix:
{code}

Check and fix:
1. Missing imports (Symbol, Function, Eq, Derivative from sympy)
2. Undefined variables - ensure all are defined before use
3. Syntax errors
4. For undefined variables, determine if they should be Symbol or Function

CRITICAL: Make the code executable. If it already executes, return it unchanged.

Return JSON:
{{
    "executable": true/false,
    "errors_fixed": [...],
    "corrected_code": "# complete executable code"
}}
""".format(code=ode_str)
        
        response = self.client.run_chat_completion(prompt)
        result = json.loads(response.message.content.strip())
        
        # Test execution
        executable = self._test_execution(result['corrected_code'])
        
        return {
            'ode_str': result['corrected_code'],
            'execution_report': {
                'errors_fixed': result.get('errors_fixed', []),
                'executable': executable
            },
            'phase': 'execution_correction',
            'status': 'complete'
        }
    
    def _test_execution(self, code: str) -> bool:
        try:
            namespace = {'sympy': sympy}
            exec(code, namespace)
            return True
        except:
            return False

# PHASE 3: VALIDATION AGENTS
class ValidationAggregator(BaseAgent):
    """Aggregates validation sub-agents"""
    
    def __init__(self, client):
        super().__init__(client)
        self.sub_agents = {
            'parameter': ParameterValidator(client),
            'time_dep': TimeDependencyChecker(client),
            'concept': ConceptGrounder(client)
        }
    
    def process(self, input_data: Dict) -> Dict:
        results = {}
        current_code = input_data['ode_str']
        
        for name, agent in self.sub_agents.items():
            agent_input = {'ode_str': current_code}
            if name == 'concept' and 'concepts' in input_data:
                agent_input['concepts'] = input_data['concepts']
            
            result = agent.process(agent_input)
            results[name] = result
            current_code = result.get('ode_str', current_code)
        
        return {
            'ode_str': current_code,
            'validation_reports': results,
            'phase': 'validation',
            'status': 'complete'
        }

class ParameterValidator(BaseAgent):
    """Check parameter consistency"""
    
    def process(self, input_data: Dict) -> Dict:
        ode_str = input_data['ode_str']
        
        prompt = """
Check parameter definitions and consistency in this SymPy code:

{code}

Verify:
1. All parameters in equations are defined
2. No unused parameter definitions
3. Consistent notation (subscripts, Greek letters)
4. Parameters are Symbols, state variables are Functions

Return JSON:
{{
    "issues": [...],
    "missing_params": [...],
    "unused_params": [...],
    "suggestions": [...]
}}
""".format(code=ode_str)
        
        response = self.client.run_chat_completion(prompt)
        return json.loads(response.message.content.strip())

class TimeDependencyChecker(BaseAgent):
    """Validate time dependency classification"""
    
    def process(self, input_data: Dict) -> Dict:
        ode_str = input_data['ode_str']
        
        prompt = """
Check time-dependency in this SymPy code:

{code}

Verify:
1. Variables with d/dt are Functions
2. Parameters without d/dt are Symbols
3. Consistent use of (t) notation

Return JSON:
{{
    "issues": [...],
    "wrong_classifications": [...],
    "suggestions": [...]
}}
""".format(code=ode_str)
        
        response = self.client.run_chat_completion(prompt)
        return json.loads(response.message.content.strip())

class ConceptGrounder(BaseAgent):
    """Validate concept grounding"""
    
    def process(self, input_data: Dict) -> Dict:
        ode_str = input_data['ode_str']
        concepts = input_data.get('concepts', {})
        
        # Use existing concept grounding logic
        from mira.sources.sympy_ode.llm_util import get_concepts_from_odes
        
        if not concepts:
            concepts = get_concepts_from_odes(ode_str, self.client)
        
        return {
            'concepts': concepts,
            'grounding_report': {'status': 'complete'}
        }

# MATHEMATICAL VALIDATION AGENTS
class MathematicalAggregator(BaseAgent):
    """Aggregates mathematical validation sub-agents"""
    
    def __init__(self, client):
        super().__init__(client)
        self.sub_agents = {
            'conservation': ConservationChecker(client),
            'dimensional': DimensionalValidator(client),
            'term_balance': TermBalanceChecker(client),
            'arithmetic': ArithmeticScanner(client)
        }
    
    def process(self, input_data: Dict) -> Dict:
        results = {}
        
        for name, agent in self.sub_agents.items():
            result = agent.process(input_data)
            results[name] = result
        
        return {
            'mathematical_reports': results,
            'phase': 'mathematical_validation',
            'status': 'complete'
        }

class ConservationChecker(BaseAgent):
    """Check conservation laws"""
    
    def process(self, input_data: Dict) -> Dict:
        ode_str = input_data['ode_str']
        
        prompt = """
Check conservation principles in these ODEs:

{code}

Verify:
1. Population conservation (outflows = inflows)
2. Mass/energy balance where applicable
3. Symmetry in bidirectional flows

Return JSON:
{{
    "conservation_violations": [...],
    "suggestions": [...]
}}
""".format(code=ode_str)
        
        response = self.client.run_chat_completion(prompt)
        return json.loads(response.message.content.strip())

class DimensionalValidator(BaseAgent):
    """Check dimensional consistency"""
    
    def process(self, input_data: Dict) -> Dict:
        # Similar structure to ConservationChecker
        pass

class TermBalanceChecker(BaseAgent):
    """Check term balance in equations"""
    
    def process(self, input_data: Dict) -> Dict:
        # Similar structure
        pass

class ArithmeticScanner(BaseAgent):
    """Scan for arithmetic errors"""
    
    def process(self, input_data: Dict) -> Dict:
        ode_str = input_data['ode_str']
        
        prompt = """
Check arithmetic operations in these ODEs:

{code}

Verify:
1. Correct use of + vs * operators
2. Proper parentheses placement
3. No missing /N normalization terms
4. Consistent coefficient usage

Return JSON:
{{
    "arithmetic_issues": [...],
    "operator_errors": [...],
    "suggestions": [...]
}}
""".format(code=ode_str)
        
        response = self.client.run_chat_completion(prompt)
        return json.loads(response.message.content.strip())

# PHASE 4: UNIFIED ERROR CORRECTOR
class UnifiedErrorCorrector(BaseAgent):
    """Phase 4: Correct all identified issues"""
    
    def process(self, input_data: Dict) -> Dict:
        ode_str = input_data['ode_str']
        validation_reports = input_data.get('validation_reports', {})
        math_reports = input_data.get('mathematical_reports', {})
        
        # Aggregate all issues
        all_issues = self._aggregate_issues(validation_reports, math_reports)
        
        if not all_issues:
            return {
                'ode_str': ode_str,
                'corrections_made': [],
                'phase': 'correction',
                'status': 'no_corrections_needed'
            }
        
        prompt = """
You are the unified error corrector. Fix ALL identified issues.

Current code:
{code}

Issues to fix:
{issues}

Apply ALL corrections while:
1. Preserving original naming and structure
2. Maintaining mathematical correctness
3. Ensuring code remains executable

Return JSON:
{{
    "corrected_code": "# fully corrected code",
    "corrections_applied": [...],
    "remaining_warnings": [...]
}}
""".format(code=ode_str, issues=json.dumps(all_issues))
        
        response = self.client.run_chat_completion(prompt)
        result = json.loads(response.message.content.strip())
        
        return {
            'ode_str': result['corrected_code'],
            'corrections_report': result,
            'phase': 'correction',
            'status': 'complete'
        }
    
    def _aggregate_issues(self, val_reports, math_reports):
        issues = []
        
        # Extract issues from validation reports
        for report in val_reports.values():
            if 'issues' in report:
                issues.extend(report['issues'])
        
        # Extract issues from mathematical reports
        for report in math_reports.values():
            if 'conservation_violations' in report:
                issues.extend(report['conservation_violations'])
            if 'arithmetic_issues' in report:
                issues.extend(report['arithmetic_issues'])
        
        return issues

# PHASE 5: QUANTITATIVE EVALUATOR
class QuantitativeEvaluator(BaseAgent):
    """Phase 5: Final quality assessment"""
    
    def process(self, input_data: Dict) -> Dict:
        all_reports = {
            'execution': input_data.get('execution_report', {}),
            'validation': input_data.get('validation_reports', {}),
            'mathematical': input_data.get('mathematical_reports', {}),
            'corrections': input_data.get('corrections_report', {})
        }
        
        score = self._calculate_quality_score(all_reports)
        
        return {
            'quality_score': score,
            'phase': 'evaluation',
            'status': 'complete',
            'final_ode_str': input_data['ode_str'],
            'final_concepts': input_data.get('concepts', {})
        }
    
    def _calculate_quality_score(self, reports):
        weights = {
            'execution': 0.30,
            'parameters': 0.15,
            'time_dependency': 0.15,
            'mathematical': 0.25,
            'corrections': 0.15
        }
        
        scores = {}
        
        # Execution score
        exec_report = reports.get('execution', {})
        scores['execution'] = 1.0 if exec_report.get('executable', False) else 0.0
        
        # Other scores based on issue counts
        val_reports = reports.get('validation', {})
        param_issues = len(val_reports.get('parameter', {}).get('issues', []))
        scores['parameters'] = max(0, 1.0 - (param_issues * 0.1))
        
        # Mathematical score
        math_reports = reports.get('mathematical', {})
        math_issues = sum(
            len(r.get('issues', []) + r.get('violations', []))
            for r in math_reports.values()
        )
        scores['mathematical'] = max(0, 1.0 - (math_issues * 0.1))
        
        # Calculate weighted total
        total = sum(scores.get(k, 0) * v for k, v in weights.items())
        
        return {
            'total_score': total,
            'component_scores': scores,
            'confidence': 'high' if total > 0.85 else 'medium' if total > 0.70 else 'low'
        }