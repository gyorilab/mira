import gc
import logging

from .base import PdfExtractor

logger = logging.getLogger(__name__)


class PaddleOCRExtractor(PdfExtractor):
    """Extract equations from a PDF using PaddleOCR (PP-StructureV3).

    Supports both text and image modes.

    Install (CPU):
        pip install paddleocr paddlepaddle
        pip install "paddlex[ocr]"

    Install (GPU):
        pip install paddleocr "paddlex[ocr]"
    """

    supported_methods = {"text", "image"}

    _pipeline_singleton = None

    def _run_pipeline(self):
        from paddleocr import PPStructureV3

        if PaddleOCRExtractor._pipeline_singleton is None:
            logger.info("Initializing PPStructureV3 pipeline (first call) ")
            PaddleOCRExtractor._pipeline_singleton = PPStructureV3(
                use_formula_recognition=True,
                use_table_recognition=False,
                enable_mkldnn=False)

        logger.info(f"Running PaddleOCR pipeline for {self.pdf_file.name}")
        results = list(
            PaddleOCRExtractor._pipeline_singleton.predict(str(self.pdf_file))
        )
        return results

    def get_pipeline_inputs(self):
        try:
            import paddleocr
        except ImportError:
            raise ImportError(
                "paddleocr is not installed. "
                "Install it with: pip install paddleocr paddlepaddle"
            )

        out_dir = self.paper_base / "paddleocr"
        out_dir.mkdir(parents=True, exist_ok=True)

        if self.ode_extraction_method == "text":
            return self._get_text_inputs(out_dir)
        else:
            return self._get_image_inputs(out_dir)

    # Text mode
    def _get_text_inputs(self, out_dir):
        import re

        md_file = out_dir / f"{self.pmid}.md"

        if md_file.is_file():
            logger.info(f"Found existing PaddleOCR output at {md_file}, "
                        f"loading from file")
            with open(md_file) as f:
                markdown_text = f.read()
        else:
            results = self._run_pipeline()
            md_parts = []
            for res in results:
                md_info = res.markdown
                if isinstance(md_info, dict):
                    md_parts.append(md_info.get("markdown_texts", ""))
                else:
                    md_parts.append(str(md_info))
            markdown_text = "\n\n".join(md_parts)

            with open(md_file, "w") as f:
                f.write(markdown_text)
            del results
            gc.collect()

        # PaddleOCR outputs display math as $$..$$ or named LaTeX environments
        display_blocks = re.findall(
            r'\$\$(.+?)\$\$', markdown_text, re.DOTALL
        )
        env_blocks = re.findall(
            r'\\begin\{(align|equation|eqnarray)\*?\}(.*?)\\end\{\1\*?\}',
            markdown_text,
            re.DOTALL,
        )
        equation_blocks = [eq.strip() for eq in display_blocks]
        equation_blocks += [body.strip() for _, body in env_blocks]

        equation_text = "\n\n".join(
            [str((eq, "latex")) for eq in equation_blocks]
        )

        self.extraction_file = str(md_file)
        return {"content_type": "text", "text_content": equation_text}

    # Image mode
    def _get_image_inputs(self, out_dir):
        import json
        import numpy as np
        from PIL import Image

        images_dir = out_dir / "images" / self.pmid
        formula_images_file = out_dir / f"{self.pmid}_formula_images.json"

        if formula_images_file.is_file():
            logger.info(f"Found existing PaddleOCR formula image manifest "
                        f"at {formula_images_file}, loading from file")
            with open(formula_images_file) as f:
                equation_img_paths = json.load(f)
        else:
            images_dir.mkdir(parents=True, exist_ok=True)
            results = self._run_pipeline()

            equation_img_paths = []
            for page_idx, res in enumerate(results):
                d = res.json if hasattr(res, "json") else res
                d = d.get("res", d) if isinstance(d, dict) else d

                formula_list = d.get("formula_res_list") or []
                if not formula_list:
                    continue

                page_img = None
                for key in ("doc_preprocessor_image", "input_img", "img",
                            "image"):
                    candidate = d.get(key)
                    if candidate is not None:
                        page_img = candidate
                        break
                if page_img is None and hasattr(res, "img") and res.img:
                    page_img = next(iter(res.img.values()), None)

                if page_img is None:
                    continue

                if isinstance(page_img, np.ndarray):
                    page_img = Image.fromarray(page_img)
                elif isinstance(page_img, str):
                    page_img = Image.open(page_img)

                for eq_idx, formula in enumerate(formula_list):
                    bbox = (formula.get("dt_polys")
                            or formula.get("bbox")
                            or formula.get("coordinate")
                            or formula.get("block_bbox"))
                    if bbox is None:
                        continue

                    bbox_flat = np.array(bbox).reshape(-1)
                    if bbox_flat.size == 4:
                        x1, y1, x2, y2 = bbox_flat
                    else:
                        pts = np.array(bbox).reshape(-1, 2)
                        x1, y1 = pts[:, 0].min(), pts[:, 1].min()
                        x2, y2 = pts[:, 0].max(), pts[:, 1].max()

                    crop = page_img.crop(
                        (float(x1), float(y1), float(x2), float(y2))
                    )
                    img_path = images_dir / f"page{page_idx}_eq{eq_idx}.png"
                    crop.save(img_path)
                    equation_img_paths.append(img_path.as_posix())

            with open(formula_images_file, "w") as f:
                json.dump(equation_img_paths, f)

            del results
            gc.collect()

        self.extraction_file = str(formula_images_file)
        return {"content_type": "image", "image_path": equation_img_paths}
