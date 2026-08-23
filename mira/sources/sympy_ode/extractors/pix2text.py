import gc
import logging

from .base import PdfExtractor

logger = logging.getLogger(__name__)


class Pix2TextExtractor(PdfExtractor):
    """Extract equations from a PDF using Pix2Text.
    Text mode only.
    Uses Math Formula Detection (MFD) and Math Formula Recognition (MFR)
    to extract LaTeX from scientific PDFs.
    Install: pip install pix2text
    """

    supported_methods = {"text"}

    def get_pipeline_inputs(self):
        import platform
        import re

        # CoreML causes failures on Apple Silicon, fall back to CPU
        if platform.system() == "Darwin":
            import onnxruntime as ort
            _orig = ort.get_available_providers
            ort.get_available_providers = lambda: [
                p for p in _orig() if p != "CoreMLExecutionProvider"
            ]

        try:
            from pix2text import Pix2Text
        except ImportError:
            raise ImportError(
                "pix2text is not installed. "
                "Install it with: pip install pix2text"
            )

        out_dir = self.paper_base / "pix2text"
        out_dir.mkdir(parents=True, exist_ok=True)
        md_file = out_dir / f"{self.pmid}.md"

        if md_file.is_file():
            logger.info(f"Found existing Pix2Text output at {md_file}, "
                        f"loading from file")
            with open(md_file) as f:
                markdown_text = f.read()
        else:
            logger.info(f"Running Pix2Text pipeline for {self.pdf_file.name}")
            p2t = Pix2Text.from_config(enable_formula=True,enable_table=False,)
            doc = p2t.recognize_pdf(str(self.pdf_file),resized_shape=768,)
            markdown_text = doc.to_markdown(
                out_dir=str(out_dir),
                markdown_fn=f"{self.pmid}.md",
            )
            with open(md_file, "w") as f:
                f.write(markdown_text)
            del p2t
            del doc
            gc.collect()

        display_blocks = re.findall(
            r'\$\$(.+?)\$\$', markdown_text, re.DOTALL
        )
        env_blocks = re.findall(
            r'\\begin\{(align|equation|eqnarray|cases|array|matrix)\*?\}(.*?)\\end\{\1\*?\}',
            markdown_text,
            re.DOTALL,
        )
        equation_blocks = [eq.strip() for eq in display_blocks]
        equation_blocks += [body.strip() for _, body in env_blocks]

        equation_text = "\n\n".join(
            [str((eq, "latex")) for eq in equation_blocks])

        self.extraction_file = str(md_file)
        return {"content_type": "text", "text_content": equation_text}
