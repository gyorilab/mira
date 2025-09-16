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
    """Fix execution errors with iteration"""
    
    def process(self, input_data: Dict) -> Dict:
        ode_str = input_data['ode_str']
        max_attempts = 3
        
        for attempt in range(max_attempts):
            if self._test_execution(ode_str):
                return {
                    'ode_str': ode_str,
                    'execution_report': {'executable': True, 'attempts': attempt},
                    'phase': 'execution_correction',
                    'status': 'complete'
                }
            
            # Try to fix
            prompt = f"""Attempt {attempt + 1}/{max_attempts} to fix this code.
            
CODE:
{ode_str}

Return ONLY working SymPy ODE code with:
- import sympy
- t = sympy.symbols("t")  
- State variables as Functions: S = sympy.Function("S")
- Parameters as symbols: beta = sympy.symbols("beta")
- odes = [sympy.Eq(...), ...]
"""
            
            response = self.client.run_chat_completion(prompt)
            ode_str = self._clean_code_response(response.message.content)
        
        # Failed after all attempts
        if not self._test_execution(ode_str):
            return {
                'ode_str': '',
                'execution_report': {'executable': False, 'fatal': True},
                'phase': 'execution_correction', 
                'status': 'FAILED'
            }
        
        return {
            'ode_str': ode_str,
            'execution_report': {'executable': True, 'attempts': max_attempts},
            'phase': 'execution_correction',
            'status': 'complete'
        }
    
    def _test_execution(self, code: str) -> bool:
        """Test if code executes successfully"""
        try:
            namespace = {}
            exec("import sympy", namespace)
            exec(code, namespace)
            return 'odes' in namespace
        except:
            return False
    
    def _clean_code_response(self, response: str) -> str:
        """Extract code from LLM response"""
        if "```python" in response:
            return response.split("```python")[1].split("```")[0].strip()
        elif "```" in response:
            return response.split("```")[1].split("```")[0].strip()
        return response.strip()


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
            # Still check for Eq collision even if no other issues
            fixed_code = self._fix_eq_collision(ode_str)
            return {
                'ode_str': fixed_code,
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
        
        # Handle missing corrected_code gracefully
        if 'corrected_code' not in result:
            # If JSON parsing failed, try to extract code directly
            corrected_code = self._extract_code_fallback(response.message.content)
            if corrected_code is None:
                corrected_code = ode_str  # Fall back to original
            
            result = {
                'corrected_code': corrected_code,
                'corrections_applied': [],
                'remaining_warnings': ['Failed to parse corrections']
            }
        
        # Fix Eq collision before returning
        final_code = self._fix_eq_collision(result['corrected_code'])
        
        return {
            'ode_str': final_code,
            'corrections_report': result,
            'phase': 'correction',
            'status': 'complete'
        }
    
    def _aggregate_issues(self, val_reports, math_reports):
        """Aggregate all issues from validation and mathematical reports"""
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
    
    def _fix_eq_collision(self, code: str) -> str:
        """Fix Eq variable name collision with sympy.Eq"""
        # Check if there's an Eq variable that collides with sympy.Eq
        if 'Eq = sympy.Function("Eq")' in code and 'sympy.Eq(' in code:
            # Rename the variable to avoid collision
            # Replace variable definition
            code = code.replace('Eq = sympy.Function("Eq")(t)', 'E_q = sympy.Function("E_q")(t)')
            
            # Replace all uses of Eq that refer to the variable, not the class
            # This is tricky - we need to replace Eq when it's used as a variable
            # but not when it's sympy.Eq
            lines = code.split('\n')
            fixed_lines = []
            
            for line in lines:
                if 'sympy.Eq(' in line:
                    # In equation definitions, replace Eq. and Eq( but not sympy.Eq(
                    line = line.replace('Eq.diff', 'E_q.diff')
                    # Replace Eq in expressions but preserve sympy.Eq
                    import re
                    # Replace Eq when it's not preceded by sympy. or .
                    line = re.sub(r'(?<!sympy\.)(?<!\.)Eq(?=[\s\+\-\*\/\)])', 'E_q', line)
                else:
                    # In other lines, replace Eq with E_q
                    if 'Eq' in line and 'sympy.Function("Eq")' in line:
                        line = line.replace('Eq', 'E_q')
                fixed_lines.append(line)
            
            code = '\n'.join(fixed_lines)
        
        return code
    
    def _extract_code_fallback(self, response_text: str) -> Optional[str]:
        """Fallback to extract code when JSON parsing fails"""
        # Try to extract Python code blocks
        if "```python" in response_text:
            code = response_text.split("```python")[1].split("```")[0].strip()
            # Apply Eq fix to extracted code too
            return self._fix_eq_collision(code)
        elif "```" in response_text:
            code = response_text.split("```")[1].split("```")[0].strip()
            return self._fix_eq_collision(code)
        
        # Look for import statements as code start
        if "import sympy" in response_text:
            lines = response_text.split('\n')
            code_lines = []
            in_code = False
            for line in lines:
                if "import sympy" in line:
                    in_code = True
                if in_code:
                    code_lines.append(line)
                if line.strip().startswith('odes =') and ']' in response_text[response_text.index(line):]:
                    # Found the end of odes definition
                    remaining = response_text[response_text.index(line):]
                    end_idx = remaining.index(']') + 1
                    code_lines.append(remaining[:end_idx])
                    break
            
            if code_lines:
                code = '\n'.join(code_lines)
                return self._fix_eq_collision(code)
            
            return None
        
        return None


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
            '/Users/kovacs.f/Desktop/mira/notebooks/equation extraction development/correct_eqs_list.tsv'
    
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
                'error': 'No biomodel_name provided',
                'phase': 'evaluation',
            }
        
        # Get correct equations
        try:
            correct_str = self._load_correct_equations(biomodel_name)
        except Exception as e:
            return {
                'execution_success_rate': 0.0,
                'equation_accuracy_rate': 0.0,
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
        
        return {
            'execution_success_rate': execution_success,
            'equation_accuracy_rate': equation_accuracy,
            'comparison_details': comparison_details,
            'num_equations_checked': len(correct_sorted),
            'phase': 'evaluation'
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
        """Convert string representation of ODEs to SymPy objects - works with ANY symbols."""
        import re
        import sympy
        
        # First check if this is the full code or just odes
        if 'import sympy' in ode_string or 'import sp' in ode_string:
            match = re.search(r'odes\s*=\s*\[(.*?)\]', ode_string, re.DOTALL)
            if not match:
                raise ValueError("Could not find 'odes = [...]' pattern")
            content = match.group(1)
        else:
            # Assume it's already just the odes content
            content = ode_string
        
        # Find all unique symbols in the string
        # Functions: anything followed by .diff(t) or (t).diff
        function_names = set()
        # Look for X.diff patterns
        function_names.update(re.findall(r'(\w+)\.diff\(', content))
        # Also look for X(t) patterns
        function_names.update(re.findall(r'(\w+)(?=\(t\))', content))
        
        # Parameters: all other word tokens that aren't Python/SymPy keywords
        all_tokens = set(re.findall(r'\b[a-z][a-z_0-9]*\b', content, re.IGNORECASE))
        keywords = {'sympy', 'sp', 'Eq', 'diff', 't', 'import', 'def', 'class', 'None', 'True', 'False'}
        parameter_names = all_tokens - function_names - keywords
        
        # Build namespace
        namespace = {
            'sympy': sympy,
            'sp': sympy,  # Handle both aliases
            'Eq': sympy.Eq,
            't': sympy.Symbol('t')
        }
        
        # Create all functions - as function instances already evaluated at t
        for fname in function_names:
            # Check if content uses fname.diff(t) or fname(t).diff(t)
            if f'{fname}.diff' in content:
                # It's used as S.diff, so S should be S(t)
                namespace[fname] = sympy.Function(fname)(namespace['t'])
            else:
                # It's used as S(t), so S should be the Function class
                namespace[fname] = sympy.Function(fname)
        
        # Create all parameters
        for pname in parameter_names:
            namespace[pname] = sympy.Symbol(pname)
        
        # Execute just the odes list content
        code = f"odes = [{content}]"
        try:
            exec(code, namespace)
        except Exception as e:
            raise ValueError(f"Failed to execute extracted odes: {str(e)}")
        
        return namespace['odes']
    
    def _string_to_sympy_odes(self, ode_string: str) -> List:
        """Convert string representation of ODEs to SymPy objects - works with ANY symbols."""
        import re
        import sympy
        
        # Check if this is the full code or just odes
        if 'import sympy' in ode_string or 'import sp' in ode_string:
            # This is full code from Phase 5, extract just the odes part
            match = re.search(r'odes\s*=\s*\[(.*?)\]', ode_string, re.DOTALL)
            if not match:
                raise ValueError("Could not find 'odes = [...]' pattern")
            content = match.group(1)
        else:
            # Assume it's already just the odes content
            content = ode_string
        
        # Find all unique symbols in the string
        # Functions: anything followed by .diff(t) or (t).diff
        function_names = set()
        # Look for X.diff patterns
        function_names.update(re.findall(r'(\w+)\.diff\(', content))
        # Also look for X(t) patterns
        function_names.update(re.findall(r'(\w+)(?=\(t\))', content))
        
        # Parameters: all other word tokens that aren't Python/SymPy keywords
        all_tokens = set(re.findall(r'\b[a-z][a-z_0-9]*\b', content, re.IGNORECASE))
        keywords = {'sympy', 'sp', 'Eq', 'diff', 't', 'import', 'def', 'class', 'None', 'True', 'False'}
        parameter_names = all_tokens - function_names - keywords
        
        # Build namespace
        namespace = {
            'sympy': sympy,
            'sp': sympy,  # Handle both aliases
            'Eq': sympy.Eq,
            't': sympy.Symbol('t')
        }
        
        # Create all functions - as function instances already evaluated at t
        for fname in function_names:
            # Check if content uses fname.diff(t) or fname(t).diff(t)
            if f'{fname}.diff' in content:
                # It's used as S.diff, so S should be S(t)
                namespace[fname] = sympy.Function(fname)(namespace['t'])
            else:
                # It's used as S(t), so S should be the Function class
                namespace[fname] = sympy.Function(fname)
        
        # Create all parameters
        for pname in parameter_names:
            namespace[pname] = sympy.Symbol(pname)
        
        # Execute just the odes list content
        code = f"odes = [{content}]"
        try:
            exec(code, namespace)
        except Exception as e:
            raise ValueError(f"Failed to execute extracted odes: {str(e)}")
        
        return namespace['odes']
    
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
        num_eqs = result.get('num_equations_checked', 0)
        
        # Count matching equations
        comparison_details = result.get('comparison_details', [])
        if isinstance(comparison_details, list):
            num_matching = sum(1 for d in comparison_details if d.get('match', False))
        else:
            num_matching = 0
        
        
        summary = f"""
        === MIRA Equation Extraction Evaluation ===
        Execution Success: {'PASS' if exec_rate == 1.0 else 'FAIL'} ({exec_rate:.0%})
        Equation Accuracy: {num_matching}/{num_eqs} equations match ({eq_rate:.1%})
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