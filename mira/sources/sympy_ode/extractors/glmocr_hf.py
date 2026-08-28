import gc
import logging

from .base import PdfExtractor

logger = logging.getLogger(__name__)


class GlmOcrHfExtractor(PdfExtractor):
    """Extract equations from a PDF using GLM-OCR via the official SDK."""

    supported_methods = {"text"}

    def get_pipeline_inputs(self):
        import re

        try:
            from glmocr import GlmOcr
        except ImportError:
            raise ImportError(
                "glmocr[selfhosted] is not installed. "
                "Install it with: pip install 'glmocr[selfhosted]'")

        out_dir = self.paper_base / "glmocr_selfhosted"
        out_dir.mkdir(parents=True, exist_ok=True)
        md_file = out_dir / f"{self.pmid}.md"

        if md_file.is_file():
            logger.info(f"Found existing self-hosted GLM-OCR output at {md_file}, "
                        f"loading from file")
            with open(md_file) as f:
                markdown_text = f.read()
        else:
            logger.info(f"Submitting {self.pdf_file.name} to self-hosted GLM-OCR")
            with GlmOcr() as parser:
                result = parser.parse(str(self.pdf_file))
            markdown_text = result.markdown_result

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
