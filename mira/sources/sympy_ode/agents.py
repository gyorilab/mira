import json
import textwrap
from typing import Dict
from mira.sources.sympy_ode.llm_util import (
    image_file_to_odes_str, 
    get_concepts_from_odes
)

class BaseAgent:
    """Base class for all agents"""
    
    def __init__(self, client):
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
        return {}


# PHASE 1: EXTRACTION
class ODEExtractionSpecialist(BaseAgent):
    """Phase 1: Extract ODEs from image"""
    
    def process(self, input_data: Dict) -> Dict:
        image_path = input_data['image_path']
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