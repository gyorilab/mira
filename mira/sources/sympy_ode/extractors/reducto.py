import gc
import json
import logging

from .base import PdfExtractor
from ..constants import ODE_PDF_PROMPT

logger = logging.getLogger(__name__)


def compute_reducto_cost(parse_result, extract_result, credit_rate_usd=0.015):
    """Compute real Reducto cost for one paper, using actual usage returned
    by the API for this specific call."""
    parse_credits = parse_result.usage.credits
    extract_credits = extract_result.usage.credits
    total_credits = parse_credits + extract_credits
    cost_usd = total_credits * credit_rate_usd
    return {"credits": total_credits, "cost_usd": cost_usd}


class ReductoExtractor(PdfExtractor):
    """Extract equations from a PDF using the Reducto Extract API.

    Text-mode only.

    Setup:
        pip install reductoai
        export REDUCTO_API_KEY="your_api_key"
    """

    supported_methods = {"text"}

    def get_pipeline_inputs(self):
        import os
        import json as _json

        api_key = os.environ.get("REDUCTO_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "Reducto API key not found. "
                "Set the REDUCTO_API_KEY environment variable with your API key.")

        try:
            from reducto import Reducto
        except ImportError:
            raise ImportError(
                "reductoai is not installed. "
                "Install it with: pip install reductoai")

        out_dir = self.paper_base / "reducto"
        out_dir.mkdir(parents=True, exist_ok=True)
        md_file = out_dir / f"{self.pmid}.md"
        json_file = out_dir / f"{self.pmid}.json"

        if json_file.is_file():
            logger.info(f"Found existing Reducto output at {json_file}, "
                        f"loading from file")
            with open(json_file) as f:
                equations = json.load(f)
        else:
            client = Reducto()
            upload = client.upload(file=self.pdf_file)
            parse_result = client.parse.run(input=upload.file_id)
            markdown_text = "\n\n".join(
                chunk.content for chunk in parse_result.result.chunks)
            with open(md_file, "w") as f:
                f.write(markdown_text)

            schema = {
                "type": "object",
                "properties": {
                    "equations": {
                        "type": "array",
                        "description": "Every displayed and inline mathematical equation or formula in the document, in reading order.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "latex": {"type": "string", "description": "The equation transcribed as LaTeX sourcE without surrounding $ or $$ delimiters."},
                                "format": {"type": "string", "enum": ["latex", "text"], "description": "'latex' if the equation was typeset/rendered, 'text' if it appeared as plain inline text."},
                            },
                            "required": ["latex", "format"],
                        },
                    }
                },
                "required": ["equations"],
            }

            result = client.extract.run(
                input=f"jobid://{parse_result.job_id}",
                instructions={
                    "schema": schema,
                    "system_prompt": ODE_PDF_PROMPT,
                },
                settings={"array_extract": True},
            )
            equations = result.result[0]["equations"]
            cost_info = compute_reducto_cost(parse_result, result)
            self.api_cost = cost_info["cost_usd"]

            with open(json_file, "w") as f:
                _json.dump(equations, f)

            del client, upload, parse_result, result
            gc.collect()

        equation_text = "\n\n".join([str((eq["latex"], eq["format"])) for eq in equations])

        self.extraction_file = str(json_file)
        return {"content_type": "text", "text_content": equation_text}
