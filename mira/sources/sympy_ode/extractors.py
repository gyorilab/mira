import gc
import json
import logging
import tarfile
import tempfile
import subprocess

from pathlib import Path
from pypdf import PdfWriter
from indra.literature.pubmed_client import download_package_for_pmid
from .agent_pipeline import run_multi_agent_pipeline

logger = logging.getLogger(__name__)
logging.getLogger("pypdf").setLevel(logging.ERROR)


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


class Extractor:
    """Base extractor: turn a paper into equations and run the agent pipeline.

    Subclasses implement :meth:`get_pipeline_inputs` to provide the equations
    in the form expected by ``run_multi_agent_pipeline`` (the content type and
    either text content or image paths).
    """

    def __init__(self, pmid):
        self.pmid = pmid
        self.extraction_file = None

    def get_pipeline_inputs(self):
        """Return the inputs for the multi-agent pipeline.

        Returns
        -------
        :
            A dict with a ``content_type`` and the matching payload, i.e.
            ``text_content`` or ``image_path``.
        """
        raise NotImplementedError

    def extract(self, client=None):
        """Run extraction and return the resulting pipeline result.

        Parameters
        ----------
        client :
            The OpenAI client passed through to the pipeline.

        Returns
        -------
        :
            The pipeline result, with ``extraction_file`` set to the
            intermediate file used for extraction (if any).
        """
        ode = run_multi_agent_pipeline(client=client,
                                       **self.get_pipeline_inputs())
        if ode.extraction.ode_str is None:
            logger.info(
                f"{type(self).__name__} extraction returned no result for "
                f"pmid {self.pmid}; retrying with supplementary files"
            )
            ode = self._extract_with_supplementary(client, ode)

        ode.extraction_file = self.extraction_file
        gc.collect()
        return ode

    def _extract_with_supplementary(self, client, ode):
        """Hook for subclasses that can retry using supplementary material.

        Parameters
        ----------
        client :
            The OpenAI client to pass through to a retry attempt.
        ode :
            The original (failed) pipeline result, returned unchanged if a
            subclass can't retry or the retry doesn't improve on it.

        Returns
        -------
        :
            A pipeline result — either a new one from the retry, or the
            original ``ode`` passed in. Never ``None``, so callers can rely
            on ``.extraction.ode_str`` always being accessible.
        """
        return ode


class PdfExtractor(Extractor):
    """Base for extractors that work from a downloaded PDF.

    Handles acquiring the paper's PDF, downloading and extracting the PMC
    package if needed, so PDF-based subclasses can focus on parsing equations.
    """

    # Extraction methods this extractor supports; subclasses override.
    supported_methods = {"text"}

    def __init__(self, pmid, pmc, paper_base, pmid_to_download_mapping,
                 ode_extraction_method="text"):
        super().__init__(pmid)
        if ode_extraction_method not in self.supported_methods:
            raise ValueError(
                f"{type(self).__name__} does not support extraction method "
                f"'{ode_extraction_method}' (supported: "
                f"{', '.join(sorted(self.supported_methods))})"
            )
        self.pmc = pmc
        self.paper_base = paper_base
        self.pmid_to_download_mapping = pmid_to_download_mapping
        self.ode_extraction_method = ode_extraction_method
        self.pdf_file = self._ensure_pdf()
        self._combined_pdf_file = None
        self._supplementary_pdf_file = None
        self._supplementary_pdf_searched = False

    def _ensure_pdf(self):
        """Return the path to the paper's PDF, downloading it if needed."""
        extracted_subdirectory = self.paper_base / self.pmc
        nxml_files = list(extracted_subdirectory.glob("*.nxml"))

        if not nxml_files:
            pmc_content_path = download_package_for_pmid(
                self.pmid, self.paper_base, self.pmid_to_download_mapping
            )
            with tarfile.open(pmc_content_path, "r:gz") as tar:
                tar.extractall(path=self.paper_base)

        try:
            nxml_file = list(extracted_subdirectory.glob("*.nxml"))[0]
        except IndexError:
            raise FileNotFoundError(
                f"No .nxml file found in {extracted_subdirectory}"
            )

        logger.info(f"Extracted subdirectory: {extracted_subdirectory}")

        pdf_file = nxml_file.with_suffix(".pdf")
        if not pdf_file.exists():
            raise FileNotFoundError(
                "No equivalent pdf file for downloaded .nxml file"
            )
        return pdf_file

    def _get_supplementary_pdf_file(self):
        """Return a single PDF combining the paper's supplementary
        PDF/DOCX files, creating it if needed.

        Returns
        -------
        :
            Path to the combined supplementary PDF, or ``None`` if the paper
            has no supplementary files that could be merged.
        """
        if not self._supplementary_pdf_searched:
            self._supplementary_pdf_file = self._combine_supplementary_files()
            self._supplementary_pdf_searched = True
        return self._supplementary_pdf_file

    def _combine_supplementary_files(self):
        """Merge any extra PDF/DOCX files in the paper folder into one PDF.
        The main paper itself is excluded.

        Returns
        -------
        :
            Path to the combined PDF, or ``None`` if there were no
            supplementary files, or none of them could be merged.
        """
        extracted_subdirectory = self.paper_base / self.pmc
        main_stem = self.pdf_file.stem
        combined_path = (
            extracted_subdirectory / f"{main_stem}_combined_supplementary.pdf"
        )

        candidates = sorted(
            f for f in extracted_subdirectory.glob("*")
            if f.suffix.lower() in (".pdf", ".docx")
            and f.stem != main_stem
            and f != combined_path
        )

        if not candidates:
            logger.info("No supplementary PDF/DOCX files found to combine")
            return None

        with tempfile.TemporaryDirectory(prefix="docx_to_pdf_") as tmp_dir:
            writer = PdfWriter()
            merged = 0

            for f in candidates:
                if f.suffix.lower() == ".docx":
                    pdf_path = self._convert_docx_to_pdf(f, Path(tmp_dir))
                else:
                    pdf_path = f
                if pdf_path is None:
                    continue
                try:
                    writer.append(str(pdf_path))
                    merged += 1
                except Exception:
                    logger.exception(
                        f"Failed to append {pdf_path} to combined PDF"
                    )

            if not writer.pages:
                writer.close()
                logger.warning(
                    "Supplementary files were found but none could be merged"
                )
                return None

            with open(combined_path, "wb") as out:
                writer.write(out)
            writer.close()

        logger.info(
            f"Combined {merged} supplementary file(s) into {combined_path}"
        )
        return combined_path

    @staticmethod
    def _convert_docx_to_pdf(docx_path, out_dir):
        """Convert a single .docx file to PDF using headless LibreOffice.

        Returns
        -------
        :
            The path to the converted PDF, or ``None`` on failure.
        """
        try:
            subprocess.run(
                [
                    "soffice", "--headless", "--convert-to", "pdf",
                    "--outdir", str(out_dir), str(docx_path),
                ],
                check=True,
                capture_output=True,
                timeout=120,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            logger.warning(f"Could not convert {docx_path} to PDF: {e}")
            return None

        converted = out_dir / f"{docx_path.stem}.pdf"
        return converted if converted.exists() else None

    def _extract_with_supplementary(self, client, ode):
        """Retry extraction using the paper's supplementary PDF/DOCX files."""

        supplementary_pdf = self._get_supplementary_pdf_file()
        if supplementary_pdf is None:
            # No supplementary files existed, nothing new to try.
            return ode

        original_pdf_file = self.pdf_file
        self.pdf_file = supplementary_pdf
        try:
            new_ode = run_multi_agent_pipeline(
                client=client, **self.get_pipeline_inputs()
            )
        finally:
            self.pdf_file = original_pdf_file

        # Only take the retry's result if it actually found something;
        # otherwise keep the original failed ode for consistent downstream
        # handling.
        if (
            new_ode is not None
            and new_ode.extraction.ode_str is not None
            and new_ode.extraction.concepts
        ):
            return new_ode
        return ode

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
                backend=get_optimal_backend(),
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


class MarkerExtractor(PdfExtractor):
    """Extract equations from a PDF using the Marker pipeline.

    Only text-mode extraction is supported; the equations are sent in text
    (LaTeX) format to the LLM.
    """

    supported_methods = {"text"}

    def get_pipeline_inputs(self):
        from bs4 import BeautifulSoup
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from marker.output import save_output

        out_dir = self.paper_base / "marker"
        html_file = out_dir / f"{self.pmid}.html"
        out_dir.mkdir(parents=True, exist_ok=True)

        # If the html file already exists, skip running the Marker pipeline and
        # just load the content list
        if html_file.is_file():
            with open(html_file) as f:
                soup = BeautifulSoup(f.read(), "html.parser")

        else:
            models = create_model_dict()
            converter = PdfConverter(
                artifact_dict=models,
                renderer="marker.renderers.html.HTMLRenderer"
            )
            rendered = converter(str(self.pdf_file))
            save_output(rendered, out_dir, fname_base=self.pmid)

            del converter
            del models
            del rendered
            gc.collect()

            with open(html_file) as f:
                soup = BeautifulSoup(f.read(), "html.parser")

        block_equations = soup.find_all("math", display="block")
        block_latex = [eq.get_text(strip=True) for eq in block_equations]

        equation_text = "\n\n".join([str((eq, "latex")) for eq in block_latex])

        self.extraction_file = str(html_file)
        return {"content_type": "text", "text_content": equation_text}


class XmlExtractor(Extractor):
    """Extract equations from a paper's PMC XML via the PMC S3 artifact."""

    def __init__(self, pmid, pmc):
        super().__init__(pmid)
        self.pmc = pmc

    def get_pipeline_inputs(self):
        import re
        from bs4 import BeautifulSoup
        from indra.literature.pmc_client import _get_s3_artifact

        logger.info("running xml")
        eqns = []
        resp = _get_s3_artifact(self.pmc, "xml")
        xml_data = resp.text
        soup = BeautifulSoup(xml_data, 'lxml-xml')

        tex_blocks = soup.find_all('tex-math')
        eq_type = "latex"
        if len(tex_blocks) > 0:
            for block in tex_blocks:
                raw = block.get_text()
                # Extract just the math content between \begin{document} and
                # \end{document}
                match = re.search(r'\\begin\{document\}(.*?)\\end\{document\}',
                                  raw, re.DOTALL)
                if match:
                    latex = match.group(1).strip()
                    eqns.append(latex)
        else:
            math_blocks = soup.find_all('disp-formula')
            eq_type = "text"
            for block in math_blocks:
                eqns.append(block.get_text())

        markdown_text = "\n\n".join(
            [
                str((equation, eq_type))
                for equation in eqns
            ]
        )

        self.extraction_file = "No intermediate created"
        return {"content_type": "text", "text_content": markdown_text}
