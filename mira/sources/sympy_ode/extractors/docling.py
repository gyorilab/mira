import gc
import logging

from .base import PdfExtractor

logger = logging.getLogger(__name__)


class DoclingExtractor(PdfExtractor):
    """Extract equations from a PDF using the Docling
    pipeline.
    Text-mode only.

    Install: pip install docling
    """

    supported_methods = {"text"}

    def get_pipeline_inputs(self):
        try:
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.pipeline_options import ( PdfPipelineOptions, CodeFormulaVlmOptions )
            from docling.datamodel.base_models import InputFormat
            from docling_core.types.doc import DocItemLabel
        except ImportError:
            raise ImportError(
                "docling is not installed. "
                "Install it with: pip install docling" )

        out_dir = self.paper_base / "docling"
        out_dir.mkdir(parents=True, exist_ok=True)
        json_file = out_dir / f"{self.pmid}.json"

        if json_file.is_file():
            logger.info(f"Found existing Docling output at {json_file}, "
                        f"loading from file")
            from docling_core.types.doc import DoclingDocument
            with open(json_file) as f:
                doc = DoclingDocument.model_validate_json(f.read())
        else:
            vlm_opts = CodeFormulaVlmOptions.from_preset("codeformulav2")

            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = True
            pipeline_options.do_table_structure = False
            pipeline_options.do_formula_enrichment = True
            pipeline_options.code_formula_options = vlm_opts

            converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(
                        pipeline_options=pipeline_options
                    )
                }
            )
            result = converter.convert(str(self.pdf_file))
            doc = result.document
            with open(json_file, "w") as f:
                f.write(doc.model_dump_json())
            del converter
            del result
            gc.collect()

        equations = []
        for element, _ in doc.iterate_items():
            if element.label != DocItemLabel.FORMULA:
                continue
            if hasattr(element, "orig") and element.orig:
                equations.append((element.orig.strip(), "text"))
            elif hasattr(element, "text") and element.text:
                equations.append((element.text.strip(), "latex"))

        equation_text = "\n\n".join([str((eq, fmt)) for eq, fmt in equations])

        self.extraction_file = str(json_file)
        return {"content_type": "text", "text_content": equation_text}
