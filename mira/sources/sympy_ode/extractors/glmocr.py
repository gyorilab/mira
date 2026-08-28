import gc
import logging

from .base import PdfExtractor

logger = logging.getLogger(__name__)


def compute_glm_ocr_cost(result, rate_per_million=0.03):
    """Compute the real GLM-OCR cost for one paper from actual token usage.

    Uses the actual token usage returned by the API for this specific call.

    Parameters
    ----------
    result :
        The GLM-OCR parse result carrying the token usage of this call.
    rate_per_million : float
        The price in USD per one million tokens.

    Returns
    -------
    dict
        A dict with the ``total_tokens`` and the ``cost_usd`` for this call.
    """
    usage = getattr(result, "_usage", None) or {}
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    total_tokens = input_tokens + output_tokens
    cost_usd = total_tokens * (rate_per_million / 1_000_000)
    return {"total_tokens": total_tokens, "cost_usd": cost_usd}


class GlmOcrExtractor(PdfExtractor):
    """Extract equations from a PDF using GLM-OCR.

    Text-mode only.

    Setup:
        pip install glmocr
        export GLM_API_KEY="your_api_key"
    """

    supported_methods = {"text"}

    def get_pipeline_inputs(self):
        import os
        import re

        api_key = os.environ.get("GLM_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GLM-OCR (Zhipu) API key not found. "
                "Set the GLM_API_KEY environment variable with your API key.")

        try:
            from glmocr import GlmOcr
        except ImportError:
            raise ImportError(
                "glmocr is not installed. "
                "Install it with: pip install glmocr")

        out_dir = self.paper_base / "glmocr"
        out_dir.mkdir(parents=True, exist_ok=True)
        md_file = out_dir / f"{self.pmid}.md"

        if md_file.is_file():
            logger.info(f"Found existing GLM-OCR output at {md_file}, "
                        f"loading from file")
            with open(md_file) as f:
                markdown_text = f.read()
            self.api_cost = 0.0
        else:
            logger.info(f"Submitting {self.pdf_file.name} to GLM-OCR")
            with GlmOcr(api_key=api_key) as parser:
                result = parser.parse(str(self.pdf_file))
            markdown_text = result.markdown_result

            cost_info = compute_glm_ocr_cost(result)
            self.api_cost = cost_info["cost_usd"]

            with open(md_file, "w") as f:
                f.write(markdown_text)
            del result
            gc.collect()

        display_blocks = re.findall(r'\$\$(.+?)\$\$', markdown_text, re.DOTALL)
        inline_blocks = re.findall(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', markdown_text, re.DOTALL)
        env_blocks = re.findall(r'\\begin\{(align|equation|eqnarray)\*?\}(.*?)\\end\{\1\*?\}',
            markdown_text, re.DOTALL,)
        equation_blocks = [eq.strip() for eq in display_blocks]
        equation_blocks += [eq.strip() for eq in inline_blocks]
        equation_blocks += [body.strip() for _, body in env_blocks]

        equation_text = "\n\n".join(
            [str((eq, "latex")) for eq in equation_blocks]
        )

        self.extraction_file = str(md_file)
        return {"content_type": "text", "text_content": equation_text}
