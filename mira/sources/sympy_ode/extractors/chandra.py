import gc
import logging

from .base import PdfExtractor

logger = logging.getLogger(__name__)


class ChandraExtractor(PdfExtractor):
    """Extract equations from a PDF using Chandra OCR 2.

    Text-mode only.
    Install: pip install "chandra-ocr[hf]"
    """

    supported_methods = {"text"}

    _model_singleton = None

    def _get_model(self):
        from chandra.model.hf import load_model

        if ChandraExtractor._model_singleton is None:
            logger.info("Loading Chandra model (first call this process)")
            ChandraExtractor._model_singleton = load_model()
        return ChandraExtractor._model_singleton

    def get_pipeline_inputs(self):
        import re
        try:
            from chandra.input import load_pdf_images
            from chandra.model.hf import generate_hf
            from chandra.model.schema import BatchInputItem
            from chandra.output import parse_markdown
            import pypdfium2
        except ImportError:
            raise ImportError(
                "chandra-ocr is not installed. "
                "Install it with: pip install 'chandra-ocr[hf]'"
            )

        out_dir = self.paper_base / "chandra"
        out_dir.mkdir(parents=True, exist_ok=True)
        md_file = out_dir / f"{self.pmid}.md"

        if md_file.is_file():
            logger.info(f"Found existing Chandra output at {md_file}, "
                        f"loading from file")
            with open(md_file) as f:
                markdown_text = f.read()
        else:
            logger.info(f"Running Chandra OCR on {self.pdf_file.name}")
            # Load PDF pages as images
            images = load_pdf_images(
                filepath=str(self.pdf_file),
                page_range=list(range(len(
                    pypdfium2.PdfDocument(str(self.pdf_file))
                ))),
            )
            logger.info(f"Loaded {len(images)} pages from PDF")
            model = self._get_model()
            batch = [
                BatchInputItem(image=img, prompt_type="ocr_layout")
                for img in images
            ]
            results = generate_hf(batch=batch, model=model)
            markdown_text = "\n\n".join(
                [parse_markdown(r.raw) for r in results if not r.error]
            )
            with open(md_file, "w") as f:
                f.write(markdown_text)
            del batch
            del results
            gc.collect()

        display_blocks = re.findall(r'\$\$(.+?)\$\$', markdown_text, re.DOTALL)
        inline_blocks = re.findall(r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', markdown_text, re.DOTALL)
        env_blocks = re.findall(
            r'\\begin\{(align|equation|eqnarray)\*?\}(.*?)\\end\{\1\*?\}',
            markdown_text, re.DOTALL,
        )
        equation_blocks = [eq.strip() for eq in display_blocks]
        equation_blocks += [eq.strip() for eq in inline_blocks]
        equation_blocks += [body.strip() for _, body in env_blocks]

        equation_text = "\n\n".join(
            [str((eq, "latex")) for eq in equation_blocks]
        )

        self.extraction_file = str(md_file)
        return {"content_type": "text", "text_content": equation_text}
