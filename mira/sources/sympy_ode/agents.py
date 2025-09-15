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
import re
import sympy
import pandas as pd
from typing import Dict, List, Optional

class QuantitativeEvaluator(BaseAgent):
    """
    Phase 6: Final quality assessment for MIRA equation extraction
    
    Evaluates by comparing extracted equations with ground truth using subtraction.
    """
    
    def __init__(self, client, correct_eqs_file_path: str = None):
        super().__init__(client)
        # Default path to the TSV file with correct equations
        self.correct_eqs_file_path = correct_eqs_file_path or \
            '/Users/kovacs.f/Desktop/mira/notebooks/equation extraction development/extraction error check/string mismatch check/correct_eqs_list.tsv'
    
    def process(self, input_data: Dict) -> Dict:
        """
        Process evaluation using equation comparison
        """
        ode_str = input_data.get('ode_str', '')
        biomodel_name = input_data.get('biomodel_name', '')
        
        if not biomodel_name:
            return {
                'execution_success_rate': 0.0,
                'equation_accuracy_rate': 0.0,
                'overall_score': 0.0,
                'error': 'No biomodel_name provided',
                'phase': 'evaluation',
                'status': 'failed'
            }
        
        # Get correct equations
        try:
            correct_str = self._load_correct_equations(biomodel_name)
        except Exception as e:
            return {
                'execution_success_rate': 0.0,
                'equation_accuracy_rate': 0.0,
                'overall_score': 0.0,
                'error': f'Failed to load correct equations: {str(e)}',
                'phase': 'evaluation',
                'status': 'failed'
            }
        
        # Convert to SymPy equations
        try:
            correct_odes = self._string_to_sympy_odes(correct_str)
            extracted_odes = self._string_to_sympy_odes(ode_str)
        except Exception as e:
            return {
                'execution_success_rate': 0.0,
                'equation_accuracy_rate': 0.0,
                'overall_score': 0.0,
                'error': f'Failed to convert to SymPy: {str(e)}',
                'phase': 'evaluation',
                'status': 'failed'
            }
        
        # Sort equations for proper comparison
        correct_sorted = self._sort_equations_by_lhs(correct_odes)
        extracted_sorted = self._sort_equations_by_lhs(extracted_odes)
        
        # Calculate execution success
        execution_success = self._calculate_execution_success(ode_str)
        
        # Calculate equation accuracy by comparison
        equation_accuracy, comparison_details = self._calculate_equation_accuracy(
            correct_sorted, extracted_sorted
        )
        
        # Overall score
        overall = (execution_success * 0.3) + (equation_accuracy * 0.7)
        
        return {
            'execution_success_rate': execution_success,
            'equation_accuracy_rate': equation_accuracy,
            'overall_score': overall,
            'comparison_details': comparison_details,
            'num_equations_checked': len(correct_sorted),
            'phase': 'evaluation',
            'status': 'complete',
            'final_ode_str': ode_str
        }
    
    def _load_correct_equations(self, biomodel_name: str) -> str:
        """Load correct equations from TSV file"""
        df = pd.read_csv(self.correct_eqs_file_path, sep='\t')
        
        try:
            correct_str = df[df['model'] == biomodel_name]['correct_eqs'].iloc[0]
            return correct_str
        except IndexError:
            raise ValueError(f"No correct equations found for model '{biomodel_name}'")
    
    def _string_to_sympy_odes(self, ode_string: str) -> List:
        """Convert string representation of ODEs to SymPy objects"""
        # Extract the code between 'odes = [' and ']'
        match = re.search(r'odes\s*=\s*\[(.*?)\]', ode_string, re.DOTALL)
        if not match:
            raise ValueError("Could not find 'odes = [...]' pattern")
        
        content = match.group(1)
        
        # Find all unique symbols in the string
        # Functions: anything followed by (t)
        function_names = set(re.findall(r'(\w+)(?=\(t\))', content))
        
        # Parameters: all other word tokens that aren't Python/SymPy keywords
        all_tokens = set(re.findall(r'\b[a-zA-Z_]\w*\b', content))
        keywords = {'sympy', 'Eq', 'diff', 't', 'import', 'def', 'class', 'None', 'True', 'False'}
        parameter_names = all_tokens - function_names - keywords
        
        # Build namespace
        namespace = {
            'sympy': sympy,
            'Eq': sympy.Eq,
            't': sympy.Symbol('t')
        }
        
        # Create all functions
        for fname in function_names:
            namespace[fname] = sympy.Function(fname)
        
        # Create all parameters
        for pname in parameter_names:
            namespace[pname] = sympy.Symbol(pname)
        
        code = f"odes = [{content}]"
        exec(code, namespace)
        
        return namespace['odes']
    
    def _sort_equations_by_lhs(self, equations: List) -> List:
        """Sort equations by the variable letter in the LHS derivative"""
        def get_lhs_variable(eq):
            lhs_str = str(eq.lhs)
            # Handle Derivative(S(t), t) or Derivative(S, t) format
            match = re.search(r'Derivative\(([A-Z])(?:\(t\))?,', lhs_str)
            if match:
                return match.group(1)
            # Fallback: look for any single letter variable
            match = re.search(r'([AEFHIPRS])', lhs_str)
            if match:
                return match.group(1)
            return 'Z'
        
        return sorted(equations, key=get_lhs_variable)
    
    def _calculate_execution_success(self, ode_str: str) -> float:
        """Check if the ODE string executes without errors"""
        try:
            namespace = {}
            exec("import sympy", namespace)
            exec(ode_str, namespace)
            if 'odes' in namespace:
                return 1.0
            else:
                return 0.0
        except:
            return 0.0
    
    def _calculate_equation_accuracy(self, correct_odes: List, extracted_odes: List) -> tuple:
        """
        Calculate accuracy by comparing equations using subtraction
        Returns: (accuracy_score, comparison_details)
        """
        if len(correct_odes) != len(extracted_odes):
            # Handle different number of equations
            return 0.0, {
                'error': f'Equation count mismatch: correct={len(correct_odes)}, extracted={len(extracted_odes)}'
            }
        
        comparison_details = []
        num_correct = 0
        
        for i, (eq_correct, eq_extracted) in enumerate(zip(correct_odes, extracted_odes)):
            # Calculate difference by subtraction
            try:
                diff = sympy.simplify((eq_correct.lhs - eq_correct.rhs) - 
                                     (eq_extracted.lhs - eq_extracted.rhs))
                
                # Check if difference is zero (equations match)
                is_match = diff == 0
                if is_match:
                    num_correct += 1
                
                comparison_details.append({
                    'equation_index': i,
                    'correct': str(eq_correct),
                    'extracted': str(eq_extracted),
                    'difference': str(diff),
                    'match': is_match
                })
            except Exception as e:
                comparison_details.append({
                    'equation_index': i,
                    'error': str(e),
                    'match': False
                })
        
        accuracy = num_correct / len(correct_odes) if correct_odes else 0.0
        
        return accuracy, comparison_details
    
    def get_evaluation_summary(self, result: Dict) -> str:
        """Generate evaluation summary with comparison details"""
        exec_rate = result.get('execution_success_rate', 0.0)
        eq_rate = result.get('equation_accuracy_rate', 0.0)
        overall = result.get('overall_score', 0.0)
        num_eqs = result.get('num_equations_checked', 0)
        
        # Count matching equations
        comparison_details = result.get('comparison_details', [])
        if isinstance(comparison_details, list):
            num_matching = sum(1 for d in comparison_details if d.get('match', False))
        else:
            num_matching = 0
        
        status = "PASS" if overall >= 0.85 else "NEEDS REVIEW" if overall >= 0.50 else "FAIL"
        
        summary = f"""
        === MIRA Equation Extraction Evaluation ===
        Execution Success: {'PASS' if exec_rate == 1.0 else 'FAIL'} ({exec_rate:.0%})
        Equation Accuracy: {num_matching}/{num_eqs} equations match ({eq_rate:.1%})
        Overall Score: {overall:.1%}
        Status: {status}
        """
        
        # Add details for non-matching equations
        if comparison_details and isinstance(comparison_details, list):
            non_matching = [d for d in comparison_details if not d.get('match', False)]
            if non_matching:
                summary += "\n        Non-matching equations:\n"
                for detail in non_matching[:3]:  # Show first 3 mismatches
                    idx = detail.get('equation_index', '?')
                    diff = detail.get('difference', 'N/A')
                    summary += f"        - Equation {idx}: Difference = {diff}\n"
        
        return summary