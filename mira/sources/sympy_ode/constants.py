from pathlib import Path
import json


HERE = Path(__file__).parent
PROMPTS_PATH = HERE / "prompts.json"

prompts_dict = json.loads(PROMPTS_PATH.read_text())

ODE_IMAGE_PROMPT = prompts_dict["ode-png"]
ODE_CONCEPTS_PROMPT_TEMPLATE = prompts_dict["ode-concepts"]
