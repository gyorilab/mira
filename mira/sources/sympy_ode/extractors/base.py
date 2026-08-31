import gc
import json
import logging
import tarfile
import tempfile
import subprocess

from pathlib import Path
from pypdf import PdfWriter

from indra.literature.pubmed_client import download_package_for_pmid

from ..agent_pipeline import run_multi_agent_pipeline

logger = logging.getLogger(__name__)
logging.getLogger("pypdf").setLevel(logging.ERROR)


class Extractor:
    """Base extractor: turn a paper into equations and run the agent pipeline.

    Subclasses implement :meth:`get_pipeline_inputs` to provide the equations
    in the form expected by ``run_multi_agent_pipeline`` (the content type and
    either text content or image paths).
    """

    def __init__(self, pmid):
        self.pmid = pmid
        self.extraction_file = None
        self.api_cost = 0.0

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
        ode.api_cost = self.api_cost
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
