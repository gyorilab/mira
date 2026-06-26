import gc
import json
import logging
import tarfile
import re

from indra.literature.pubmed_client import download_package_for_pmid

from .agent_pipeline import run_multi_agent_pipeline

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
        ode.extraction_file = self.extraction_file
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
            p2t = Pix2Text(enable_formula=True, enable_table=False)
            doc = p2t.recognize(str(self.pdf_file), file_type="pdf")
            markdown_text = doc.to_markdown(
                out_dir=str(out_dir),
                markdown_fn=f"{self.pmid}.md",
            )
            with open(md_file, "w") as f:
                f.write(markdown_text)
            del p2t
            del doc
            gc.collect()

        # Pix2Text outputs display math as $$..$$ or named environments
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

        if equation_blocks:
            logger.info(f"Found {len(equation_blocks)} equation blocks via "
                        f"Pix2Text output")
            equation_text = "\n\n".join(
                [str((eq, "latex")) for eq in equation_blocks]
            )
        else:
            logger.warning(
                f"No equation blocks found in Pix2Text output for "
                f"{self.pmid}, passing full markdown to pipeline"
            )
            equation_text = markdown_text

        self.extraction_file = str(md_file)
        return {"content_type": "text", "text_content": equation_text}
