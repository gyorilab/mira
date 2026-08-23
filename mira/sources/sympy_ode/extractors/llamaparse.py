import logging

from .base import PdfExtractor

logger = logging.getLogger(__name__)


def compute_llamaparse_cost(num_pages, credits_per_page=3, credits_per_1000_usd=1.25):
    """Compute estimated LlamaParse cost for one paper.
    num_pages :
        Number of pages in the PDF.
    credits_per_page :
        Credits per page for the tier used.
    credits_per_1000_usd :
        Dollars per 1000 credits ($1.25).
    """
    credits = num_pages * credits_per_page
    cost_usd = (credits / 1000) * credits_per_1000_usd
    return {"credits": credits, "cost_usd": cost_usd}


class LlamaParseExtractor(PdfExtractor):
    """Extract equations from a PDF using LlamaParse.
    Text-mode only.

    Setup:
        pip install llama-parse
        export LLAMA_CLOUD_API_KEY="your_api_key"
    """

    supported_methods = {"text"}

    def get_pipeline_inputs(self):
        import os
        import re
        import pypdfium2

        api_key = os.environ.get("LLAMA_CLOUD_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "LlamaParse API key not found. "
                "Set the LLAMA_CLOUD_API_KEY environment variable with your API key." )

        try:
            from llama_parse import LlamaParse
        except ImportError:
            raise ImportError(
                "llama-parse is not installed. "
                "Install it with: pip install llama-parse" )

        out_dir = self.paper_base / "llamaparse"
        out_dir.mkdir(parents=True, exist_ok=True)
        md_file = out_dir / f"{self.pmid}.md"

        if md_file.is_file():
            logger.info(f"Found existing LlamaParse output at {md_file}, "
                        f"loading from file")
            with open(md_file) as f:
                markdown_text = f.read()
        else:
            logger.info(f"Submitting {self.pdf_file.name} to LlamaParse")
            parser = LlamaParse(
                api_key=api_key,
                result_type="markdown",
                system_prompt=(
                    "This is a scientific paper describing a mathematical or epidemiological model, likely containing a system of ordinary differential equations (ODEs). "
                    "Preserve every mathematical equation exactly as it appears in the original text rendered as LaTeX inside $$...$$ delimiters for display equations. "
                    "Do not simplify,paraphrase or omit any subscripts, superscripts or Greek letters - reproduce variable and parameter names precisely as written (e.g. preserve S, I, R, "
                    "beta, gamma and any subscripted variants like S_q or E_1 exactly as they appear). Pay special attention to derivative notation and preserve it."
                ),
            )
            documents = parser.load_data(str(self.pdf_file))
            markdown_text = "\n\n".join(doc.text for doc in documents)

            with open(md_file, "w") as f:
                f.write(markdown_text)

        # Compute and store the estimated API cost for this paper
        num_pages = len(pypdfium2.PdfDocument(str(self.pdf_file)))
        cost_info = compute_llamaparse_cost(num_pages)
        self.api_cost = cost_info["cost_usd"]

        display_blocks = re.findall(r'\$\$(.+?)\$\$', markdown_text, re.DOTALL)
        bracket_blocks = re.findall(r'\\\[(.+?)\\\]', markdown_text, re.DOTALL)
        equation_blocks = [eq.strip() for eq in display_blocks]
        equation_blocks += [eq.strip() for eq in bracket_blocks]

        equation_text = "\n\n".join(
            [str((eq, "latex")) for eq in equation_blocks]
        )

        self.extraction_file = str(md_file)
        return {"content_type": "text", "text_content": equation_text}
