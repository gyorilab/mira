import json
import logging

from .base import PdfExtractor

logger = logging.getLogger(__name__)


def get_optimal_backend() -> str:
    """
    Automatically select backend based on available VRAM.
    Returns 'vlm-vllm-engine' for 8GB+, 'pipeline' otherwise. The vllm engine
    has higher accuracy and is faster.
    Check the "Local Deployment" section of the README.md here:
    https://github.com/opendatalab/MinerU/blob/master/README.md.
    """
    import torch

    if not torch.cuda.is_available():
        logger.warning("CUDA not available, using pipeline backend with CPU")
        return "pipeline"

    # Get total VRAM in GB
    total_vram_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    logger.info(f"Detected {total_vram_gb:.2f} GB VRAM")

    if total_vram_gb >= 8.0:
        logger.info("Using VLM backend (faster, requires 8GB+ VRAM)")
        return "vlm-vllm-engine"
    else:
        logger.info(
            f"Using pipeline backend with CUDA (VLM requires 8GB+, you have "
            f"{total_vram_gb:.2f}GB)"
        )
        return "pipeline"

class MineruExtractor(PdfExtractor):
    """Extract equations from a PDF using the MinerU pipeline."""

    supported_methods = {"text", "image"}

    def _find_parse_method_path(self, pdf_name):
        vlm_path = self.paper_base / pdf_name / "vlm"
        if vlm_path.exists():
            return vlm_path
        auto_path = self.paper_base / pdf_name / "auto"
        if auto_path.exists():
            return auto_path
        return None

    def get_pipeline_inputs(self):
        from mineru.cli.common import do_parse, read_fn

        # Need filename without extension
        pdf_name = self.pdf_file.stem
        content_list_file = None

        parse_method_path = self._find_parse_method_path(pdf_name)
        if parse_method_path:
            content_list_file = \
                parse_method_path / f"{pdf_name}_content_list.json"
        else:
            logger.info(f"No parse method directory found for {pdf_name} in "
                        f"{self.paper_base}, running MinerU pipeline")

        # If the content list file already exists, skip running the MinerU
        # pipeline and just load the content list
        if content_list_file and content_list_file.is_file():
            with open(content_list_file) as f:
                logger.info(f"Found existing content list file at "
                            f"{content_list_file}, loading content list "
                            f"from file")
                content_list = json.load(f)
        else:
            do_parse(
                output_dir=self.paper_base.as_posix(),
                pdf_file_names=[pdf_name],
                pdf_bytes_list=[read_fn(self.pdf_file)],
                p_lang_list=["en"],
                backend=get_optimal_backend(self.ode_extraction_method),
                parse_method="auto",
                formula_enable=True,
                table_enable=False,
                f_draw_layout_bbox=False,
                f_draw_span_bbox=False,
                f_dump_md=True,
                f_dump_middle_json=False,
                f_dump_model_output=False,
                f_dump_orig_pdf=False,
                f_dump_content_list=True,
            )
            parse_method_path = self._find_parse_method_path(pdf_name)
            if parse_method_path is None:
                raise FileNotFoundError(
                    f"MinerU produced no parse method directory for "
                    f"{pdf_name} in {self.paper_base}"
                )
            content_list_file = \
                parse_method_path / f"{pdf_name}_content_list.json"

            with open(content_list_file) as f:
                content_list = json.load(f)

        equation_content = [content for content in content_list
                            if content.get("type") == "equation"]

        # If we use image mode we need to require that the image
        # paths exist for the given equations
        if self.ode_extraction_method == "image":
            equation_content = [content for content in equation_content
                                if content.get("img_path")]

        self.extraction_file = str(content_list_file)

        if self.ode_extraction_method == "text":
            markdown_text = "\n\n".join(
                [
                    str((equation["text"], equation["text_format"]))
                    for equation in equation_content
                ]
            )
            return {"content_type": "text", "text_content": markdown_text}
        else:
            equation_img_paths = [
                (parse_method_path / equation['img_path']).as_posix()
                for equation in equation_content
            ]
            return {"content_type": "image",
                    "image_path": equation_img_paths}
