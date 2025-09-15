# agents.py
import json
import sympy
from typing import Dict, Tuple, Optional, List
from abc import ABC, abstractmethod

class BaseAgent:
    """Base class for all agents"""
    
    def __init__(self, client): # OpenAI client for every agent
        self.client = client
        self.name = self.__class__.__name__

    def _parse_json_response(self, response_text: str) -> dict: # same method for each agent for parsing the LLM response
        """Safely parse JSON from LLM response"""
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        try:
            return json.loads(response_text.strip())
        except json.JSONDecodeError:
            # Return safe defaults
            return {}
    
    @abstractmethod 
    def process(self, input_data: Dict) -> Dict: # same format for all methods for each agent
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

# PHASE 2: CONCEPT GROUNDING

class ConceptGrounder(BaseAgent):
    """Phase 2: Extract concepts from ODE string - separate agent"""
    
    def process(self, input_data: Dict) -> Dict:
        ode_str = input_data['ode_str']
        
        from mira.sources.sympy_ode.llm_util import get_concepts_from_odes
        
        try:
            concepts = get_concepts_from_odes(ode_str, self.client)
            status = 'complete'
        except Exception as e:
            concepts = None
            status = f'failed: {str(e)}'
        
        return {
            'concepts': concepts,
            'phase': 'concept_grounding',
            'status': status
        }

# PHASE 3: EXECUTION ERROR CHECK & CORRECTION
class ExecutionErrorCorrector(BaseAgent):
    """Check and fix execution errors"""
    
    def process(self, input_data: Dict) -> Dict:
        ode_str = input_data['ode_str']
        
        # First check if it already executes
        if self._test_execution(ode_str):
            return {
                'ode_str': ode_str,
                'execution_report': {
                    'errors_fixed': [],
                    'executable': True
                },
                'phase': 'execution_correction',
                'status': 'already_executable'
            }
        
        # Fix with LLM
        prompt = """Fix execution errors in this code. Return ONLY the corrected Python code.

{code}

Fix: missing imports, undefined variables, syntax errors.
Return only executable Python code.""".format(code=ode_str)
        
        response = self.client.run_chat_completion(prompt)
        corrected_code = self._clean_code_response(response.message.content)
        
        executable = self._test_execution(corrected_code)
        
        return {
            'ode_str': corrected_code if executable else ode_str,
            'execution_report': {
                'errors_fixed': ['execution errors'] if executable else [],
                'executable': executable
            },
            'phase': 'execution_correction',
            'status': 'complete'
        }
    
    def _clean_code_response(self, response: str) -> str:
        """Extract code from response"""
        if "```python" in response:
            response = response.split("```python")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        return response.strip()
    
    def _test_execution(self, code: str) -> bool:
        try:
            namespace = {'sympy': sympy}
            exec(code, namespace)
            return 'odes' in namespace
        except:
            return False


# PHASE 4: VALIDATION AGENTS
class ValidationAggregator(BaseAgent):
    """Phase 4: Aggregates validation sub-agents"""
    
    def __init__(self, client):
        super().__init__(client)
        self.sub_agents = {
            'parameter': ParameterValidator(client),
            'time_dep': TimeDependencyChecker(client)
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
        return self._parse_json_response(response.message.content)

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
        return self._parse_json_response(response.message.content)

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
            'arithmetic': ArithmeticScanner(client),
            'structural': StructuralChecker(client)
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
        return self._parse_json_response(response.message.content)


class StructuralChecker(BaseAgent):
    """Check mathematical structure without units"""
    
    def process(self, input_data: Dict) -> Dict:
        ode_str = input_data['ode_str']

        prompt = """

    Check structural rules in these ODEs:

{code}

Checks:
1. **Sign Convention**: Loss terms should be negative; gain terms 
   should be positive.

2. **Interaction Balance**: Interaction terms must appear with 
   opposite signs in coupled equations.

3. **Denominator Safety**: Never divide by a bare state variable.

4. **Power Law Rationality**: Use integer exponents unless fractional 
   powers have clear justification.

5. **Transfer Symmetry**: Material leaving one compartment must enter 
   another at the same rate.

6. **Variable Connectivity**: Every state variable should appear in 
   at least two equations.



Return JSON:
{{
    "structural_issues": [...],
    "suggestions": [...]
}}
""".format(code=ode_str)
        
        response = self.client.run_chat_completion(prompt)
        return self._parse_json_response(response.message.content)



# PHASE 5: UNIFIED ERROR CORRECTOR
class UnifiedErrorCorrector(BaseAgent):
    """Phase 5: Correct all identified issues"""
    
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
        result = self._parse_json_response(response.message.content)
        
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

# PHASE 6: QUANTITATIVE EVALUATOR
class QuantitativeEvaluator(BaseAgent):
    """
    Phase 6: Final quality assessment for MIRA equation extraction
    
    Evaluates two primary metrics:
    1. Execution Success Rate - Binary check if equation executes without errors
    2. Symbol Accuracy Rate - Percentage of correctly extracted/validated symbols
    """
    
    def process(self, input_data: Dict) -> Dict:
        """
        Process evaluation with simplified dual-metric system
        """
        # Calculate execution success (binary: 0 or 1)
        execution_success = self._calculate_execution_success(
            input_data.get('execution_report', {})
        )
        
        # Calculate symbol accuracy (percentage: 0.0 to 1.0)
        symbol_accuracy = self._calculate_symbol_accuracy(
            input_data.get('validation_reports', {}),
            input_data.get('mathematical_reports', {})
        )
        
        return {
            'execution_success_rate': execution_success,
            'symbol_accuracy_rate': symbol_accuracy,
            'overall_score': (execution_success * 0.5) + (symbol_accuracy * 0.5),
            'phase': 'evaluation',
            'status': 'complete',
            'final_ode_str': input_data['ode_str'],
            'final_concepts': input_data.get('concepts', {})
        }
    
    def _calculate_execution_success(self, exec_report: Dict) -> float:
        """
        Returns 1.0 if equation executes successfully, 0.0 otherwise
        
        This is a binary metric - the equation either runs or it doesn't.
        """
        return 1.0 if exec_report.get('executable', False) else 0.0
    
    def _calculate_symbol_accuracy(self, validation_reports: Dict, 
                                   mathematical_reports: Dict) -> float:
        """
        Calculate accuracy of symbol extraction and validation
        
        Returns percentage of symbols correctly identified and validated
        """
        # Count total symbols/parameters found
        total_symbols = 0
        correct_symbols = 0
        
        # Check parameter validation
        param_report = validation_reports.get('parameter', {})
        if 'parameters' in param_report:
            params = param_report['parameters']
            total_symbols += len(params)
            # Count parameters without issues
            param_issues = len(param_report.get('issues', []))
            correct_symbols += max(0, len(params) - param_issues)
        
        # Check mathematical symbol validation
        for report_type, report in mathematical_reports.items():
            if 'symbols' in report or 'variables' in report:
                symbols = report.get('symbols', report.get('variables', []))
                total_symbols += len(symbols)
                # Count symbols without issues
                issues = len(report.get('issues', [])) + len(report.get('violations', []))
                correct_symbols += max(0, len(symbols) - issues)
        
        # Return accuracy as percentage
        if total_symbols == 0:
            return 1.0  # No symbols to validate = perfect score
        
        return correct_symbols / total_symbols
    
    def get_evaluation_summary(self, execution_rate: float, 
                               symbol_rate: float) -> str:
        """
        Generate human-readable evaluation summary
        """
        status = "PASS" if execution_rate == 1.0 and symbol_rate >= 0.8 else "NEEDS REVIEW"
        exec_status = "PASS" if execution_rate == 1.0 else "FAIL"
        
        return f"""
        === MIRA Equation Extraction Evaluation ===
        Execution Success: {exec_status} ({execution_rate:.0%})
        Symbol Accuracy: {symbol_rate:.1%}
        Overall Status: {status}
        """