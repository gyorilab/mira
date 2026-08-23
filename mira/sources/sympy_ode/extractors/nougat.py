import gc
import logging

from .base import PdfExtractor

logger = logging.getLogger(__name__)


class NougatExtractor(PdfExtractor):
    """Extract equations from a PDF using Meta's Nougat model.

    Text-mode only.

    Install:
        pip install "transformers>=4.40" pypdfium2 torch
    """

    supported_methods = {"text"}

    _model_singleton = None
    _processor_singleton = None

    @classmethod
    def _get_model_and_processor(cls):
        from transformers import NougatProcessor, VisionEncoderDecoderModel
        import torch

        if cls._model_singleton is None:
            logger.info("Loading Nougat model (first call this process)")
            cls._processor_singleton = NougatProcessor.from_pretrained("facebook/nougat-base")
            model = VisionEncoderDecoderModel.from_pretrained("facebook/nougat-base")
            device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
            model.to(device)
            cls._model_singleton = model
        return cls._model_singleton, cls._processor_singleton

    def get_pipeline_inputs(self):
        import re
        import pypdfium2

        out_dir = self.paper_base / "nougat"
        out_dir.mkdir(parents=True, exist_ok=True)
        md_file = out_dir / f"{self.pmid}.md"

        if md_file.is_file():
            logger.info(f"Found existing Nougat output at {md_file}, "
                        f"loading from file")
            with open(md_file) as f:
                markdown_text = f.read()
        else:
            logger.info(f"Running Nougat OCR on {self.pdf_file.name}")
            model, processor = self._get_model_and_processor()
            device = next(model.parameters()).device
            pdf = pypdfium2.PdfDocument(str(self.pdf_file))
            page_texts = []
            for page in pdf:
                image = page.render(scale=144 / 72).to_pil().convert("RGB")
                pixel_values = processor(image, return_tensors="pt").pixel_values

                outputs = model.generate(
                    pixel_values.to(device),
                    min_length=1,
                    max_new_tokens=4096,
                    bad_words_ids=[[processor.tokenizer.unk_token_id]],
                )
                sequence = processor.batch_decode(
                    outputs, skip_special_tokens=True)[0]
                sequence = processor.post_process_generation(
                    sequence, fix_markdown=True)
                page_texts.append(sequence)

            pdf.close()
            markdown_text = "\n\n".join(page_texts)

            with open(md_file, "w") as f:
                f.write(markdown_text)
            gc.collect()

        display_blocks = re.findall(r'\$\$(.+?)\$\$', markdown_text, re.DOTALL)
        inline_blocks = re.findall(
            r'(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)', markdown_text, re.DOTALL)
        bracket_blocks = re.findall(r'\\\[(.+?)\\\]', markdown_text, re.DOTALL)
        env_blocks = re.findall(
            r'\\begin\{(align|equation|eqnarray)\*?\}(.*?)\\end\{\1\*?\}',
            markdown_text, re.DOTALL,)
        equation_blocks = [eq.strip() for eq in display_blocks]
        equation_blocks += [eq.strip() for eq in inline_blocks]
        equation_blocks += [eq.strip() for eq in bracket_blocks]
        equation_blocks += [body.strip() for _, body in env_blocks]

        equation_text = "\n\n".join([str((eq, "latex")) for eq in equation_blocks])

        self.extraction_file = str(md_file)
        return {"content_type": "text", "text_content": equation_text}
