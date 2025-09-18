import json
import textwrap
import re
import sympy
import pandas as pd
from typing import Dict, List, Optional
from mira.sources.sympy_ode.llm_util import image_file_to_odes_str, \
    get_concepts_from_odes


class BaseAgent:
    """Base class for all agents"""
    
    def __init__(self, client): # OpenAI client for every agent
        self.client = client
        self.name = self.__class__.__name__

    def process(self, input_data: Dict) -> Dict:
        raise NotImplementedError("Each agent must implement its own process method")


def parse_json_response(response_text: str) -> dict:
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


# PHASE 1: EXTRACTION
class ODEExtractionSpecialist(BaseAgent):
    """Phase 1: Extract ODEs from image"""
    
    def process(self, input_data: Dict) -> Dict:
        image_path = input_data['image_path']
        # Use existing extraction logic
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
            prompt = f"""
                Attempt {attempt + 1}/{max_attempts} to fix this code.
            
                CODE:
                {ode_str}

                Return ONLY working SymPy ODE code with:
                - import sympy
                - t = sympy.symbols("t")  
                - State variables as Functions: S = sympy.Function("S")
                - Parameters as symbols: beta = sympy.symbols("beta")
                - Python keywords converted to format with added underscore 
                - odes = [sympy.Eq(...), ...]
            """
            prompt = textwrap.dedent(prompt).strip()
            
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
        
        prompt = f"""
            Check parameter definitions and consistency in this SymPy code:

            {ode_str}

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
        """
        prompt = textwrap.dedent(prompt).strip()
        
        response = self.client.run_chat_completion(prompt)
        result = parse_json_response(response.message.content)
        return {
            'ode_str': ode_str,
            **result
        }


class TimeDependencyChecker(BaseAgent):
    """Validate time dependency classification"""
    
    def process(self, input_data: Dict) -> Dict:
        ode_str = input_data['ode_str']
        
        prompt = f"""
            Check time-dependency in this SymPy code:

            {ode_str}

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
        """
        prompt = textwrap.dedent(prompt).strip()
        
        response = self.client.run_chat_completion(prompt)
        result = parse_json_response(response.message.content)
        return {
            'ode_str': ode_str,
            **result
        }

class VariableSymbolValidator(BaseAgent):
    """Check and suggest fixes for mismatches between variable names and symbol definitions"""
    
    def process(self, input_data: Dict) -> Dict:
        ode_str = input_data['ode_str']
        
        prompt = f"""
            Check for mismatches between variable names and symbol definitions:

            {ode_str}

            Look for parameter definition lines and check if variable names match symbol strings.

            Rules:
            1. Fix any variable name that doesn't match its symbol in the string
            2. Any variable containing an underscore should contain it as a symbol too
            3. Any variable containing a subscript and/or superscript should contain it as a symbol too
            4. Any variable containing a number in it should contain it as a symbol too


            Return JSON:
            {
                "issues": [
                    "Variable names don't match their symbols in the definition string"
                ],
                "suggested_fixes": [
                    "Change symbol string to match variable names exactly"
                ]
            }

            If variable names and symbols match perfectly, return empty arrays.
        """
        prompt = textwrap.dedent(prompt).strip()
        
        response = self.client.run_chat_completion(prompt)
        result = parse_json_response(response.message.content)
        return {
            'ode_str': ode_str,  # ADD THIS
            **result
        }

# MATHEMATICAL VALIDATION AGENTS
class MathematicalAggregator(BaseAgent):
    """Aggregates mathematical validation sub-agents"""
    
    def __init__(self, client):
        super().__init__(client)
        self.sub_agents = {
            # 'arithmetic': ArithmeticScanner(client),
            # 'structural': StructuralChecker(client)
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


# class ArithmeticScanner(BaseAgent):
#     """Scan for arithmetic errors"""
    
#     def process(self, input_data: Dict) -> Dict:
#         ode_str = input_data['ode_str']
        
#         prompt = f"""
#             Check arithmetic operations in these ODEs:

#             {ode_str}

#             Verify:
#             1. Correct use of + vs * operators
#             2. Proper parentheses placement
#             3. Consistent coefficient usage

#             Return JSON:
#             {{
#                 "arithmetic_issues": [...],
#                 "operator_errors": [...],
#                 "suggestions": [...]
#             }}
#         """
#         prompt = textwrap.dedent(prompt).strip()

#         response = self.client.run_chat_completion(prompt)
#         return parse_json_response(response.message.content)


# class StructuralChecker(BaseAgent):
#     """Check mathematical structure without units"""
    
#     def process(self, input_data: Dict) -> Dict:
#         ode_str = input_data['ode_str']

#         prompt = f"""
#             Check structural rules in these ODEs:

#             {ode_str}

#             Checks:
#             1. Syntax Errors: Clear mathematical impossibilities (division by zero constants, malformed expressions)
#             2. Parentheses Issues: Missing parentheses that clearly change mathematical meaning
#             3. Operator Errors: Clear misuse of operators where mathematical context suggests error

#             Return JSON:
#             {{
#                 "structural_issues": [...],
#                 "suggestions": [...]
#             }}
#         """
#         prompt = textwrap.dedent(prompt).strip()
        
#         response = self.client.run_chat_completion(prompt)
#         return parse_json_response(response.message.content)



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
        
        prompt = f"""
            You are the unified error corrector. Fix ALL identified issues.

            Current code:
            {ode_str}

            Issues to fix:
            {json.dumps(all_issues)}

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
        """
        prompt = textwrap.dedent(prompt).strip()
        
        response = self.client.run_chat_completion(prompt)
        result = parse_json_response(response.message.content)
        
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
            if 'structural_issues' in report:
                issues.extend(report['structural_issues'])
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

class QuantitativeEvaluator(BaseAgent):
    """
    Phase 6: Final quality assessment for MIRA equation extraction
    
    Evaluates by comparing extracted equations with ground truth using subtraction.
    """
    
    def __init__(self, client, correct_eqs_file_path: str = None):
        super().__init__(client)
        # Fix the default path
        self.correct_eqs_file_path = correct_eqs_file_path or \
            '/Users/kovacs.f/Desktop/mira/notebooks/model_extraction/correct_eqs_list.tsv'
    
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
            correct_str = self.load_correct_equations(biomodel_name)
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
            correct_odes = self.string_to_sympy_odes(correct_str)
        except Exception as e:
            return {
                'execution_success_rate': 0.0,
                'equation_accuracy_rate': 0.0,
                'error': f'Failed to convert correct equations to SymPy: {str(e)}',
                'phase': 'evaluation',
                'status': 'failed'
            }
        
        try:
            extracted_odes = self.string_to_sympy_odes(ode_str)
        except Exception as e:
            return {
                'execution_success_rate': 0.0,
                'equation_accuracy_rate': 0.0,
                'error': f'Failed to convert extracted equations to SymPy: {str(e)}',
                'phase': 'evaluation',
                'status': 'failed'
            }
        
        # Sort equations for proper comparison
        correct_sorted = self.sort_equations_by_lhs(correct_odes)
        extracted_sorted = self.sort_equations_by_lhs(extracted_odes)
        
        # Calculate execution success
        execution_success = self.calculate_execution_success(ode_str)
        
        # Calculate equation accuracy by comparison
        equation_accuracy, comparison_details = self.calculate_equation_accuracy(
            correct_sorted, extracted_sorted
        )
        
        return {
            'execution_success_rate': execution_success,
            'equation_accuracy_rate': equation_accuracy,
            'comparison_details': comparison_details,
            'num_equations_checked': len(correct_sorted),
            'phase': 'evaluation'
        }    
    
    def load_correct_equations(self, biomodel_name: str) -> str:
        """Load correct equations from TSV file"""
        df = pd.read_csv(self.correct_eqs_file_path, sep='\t')
        
        try:
            correct_str = df[df['model'] == biomodel_name]['correct_eqs'].iloc[0]
            return correct_str
        except IndexError:
            raise ValueError(f"No correct equations found for model '{biomodel_name}'")

    def string_to_sympy_odes(self, ode_string: str) -> List:
        """Convert string representation of ODEs to SymPy objects"""
        import sympy
        import re
        
        # Check if it's actual Python code (has import or variable definitions)
        if 'import sympy' in ode_string or 'import sp' in ode_string:
            # Full code with imports
            namespace = {
                'sympy': sympy,
                'sp': sympy,
                '__builtins__': __builtins__
            }
            exec(ode_string, namespace)
            return namespace.get('odes', [])
        
        elif 'sympy.symbols' in ode_string or 't = sympy.symbols' in ode_string:
            # Partial code without imports (Phase 1 output)
            full_code = "import sympy\n" + ode_string
            namespace = {
                'sympy': sympy,
                '__builtins__': __builtins__
            }
            exec(full_code, namespace)
            return namespace.get('odes', [])
        
        else:
            # Ground truth from TSV or raw equation list
            content = ode_string.strip()
            
            # Remove quotes if present
            if content.startswith('"') and content.endswith('"'):
                content = content[1:-1]
            
            content = content.strip()
            
            # Fix indentation
            content = re.sub(r'\s*\n\s*', ' ', content)
            content = re.sub(r'\s+', ' ', content)
            content = content.strip()
            
            # Build namespace for eval
            function_names = set(re.findall(r'(\w+)\(t\)', content))
            all_tokens = set(re.findall(r'\b[a-zA-Z_]\w*\b', content))
            keywords = {'sympy', 'sp', 'Eq', 'diff', 't'}
            parameter_names = all_tokens - function_names - keywords
            
            t = sympy.Symbol('t')
            namespace = {
                'sympy': sympy,
                'Eq': sympy.Eq,
                't': t
            }
            
            for fname in function_names:
                namespace[fname] = sympy.Function(fname)
            for pname in parameter_names:
                namespace[pname] = sympy.Symbol(pname)
            
            # Eval the list
            result = eval(content, namespace)
            
            if isinstance(result, list) and len(result) == 1 and isinstance(result[0], list):
                return result[0]
            
            return result

    def sort_equations_by_lhs(self, equations: List) -> List:
        """Sort equations by their left-hand side for consistent comparison"""
        try:
            # Sort by string representation of LHS
            return sorted(equations, key=lambda eq: str(eq.lhs))
        except:
            # If sorting fails, return as is
            return equations
    
    def calculate_execution_success(self, ode_str: str) -> float:
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
    
    def calculate_equation_accuracy(self, correct_odes: List, extracted_odes: List) -> tuple:
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