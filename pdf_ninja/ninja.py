import logging
from pathlib import Path
import pdfplumber
from .builders.pdf_context import PdfContextBuilder
from .builders.parsed_pdf import PdfBuilder
from .dataclasses import PdfContext, ExtractedElements, ParsedPdf
from .exc import PdfNinjaParsingError
from .extractors.figure import FigureExtractor
from .extractors.image import ImageExtractor
from .extractors.metadata import MetadataExtractor
from .extractors.table import TableExtractor
from .extractors.text import TextExtractor
from .types import ExtractorConfig

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class PdfNinja:
    
    def __init__(self):
        self.figure_extractor = FigureExtractor()
        self.image_extractor = ImageExtractor()
        self.metadata_extractor = MetadataExtractor()
        self.table_extractor = TableExtractor()
        self.text_extractor = TextExtractor()

    def parse(self, path: Path, extractor_config: ExtractorConfig | None = None) -> ParsedPdf:
        if not extractor_config:
            extractor_config = {}
        try:
            with pdfplumber.open(path, **extractor_config.get("pdf_plumber", {})) as pdf:
                pdf_context = self._build_context(
                    path=path, 
                    pdf_plumber_obj=pdf, 
                    extractor_config=extractor_config
                )
                return self._parse(path=path, ctx=pdf_context)
        except PdfNinjaParsingError:
            raise
        except (OSError, ValueError) as e:
            raise PdfNinjaParsingError(f"Failed to open PDF with pdfplumber: {e}") from e
        except Exception as e:
            raise PdfNinjaParsingError(f"Unexpected error while parsing {path.name}: {e}") from e

    def _parse(self, path: Path, ctx: PdfContext) -> ParsedPdf:
        extracted_elements = self._extract(path, ctx)        

        return PdfBuilder(extracted_elements).build_parsed_pdf()

    def _extract(self, path: Path, ctx: PdfContext) -> ExtractedElements:
        return ExtractedElements(
            text = self.text_extractor.extract(ctx),
            tables = self.table_extractor.extract(ctx),
            images = self.image_extractor.extract(ctx),
            figures = self.figure_extractor.extract(ctx),
            meta = self.metadata_extractor.extract_metadata(path=path, pdf_reader=ctx.pypdf_reader),
        )

    def _build_context(
            self, path: Path, 
            pdf_plumber_obj: pdfplumber.pdf.PDF, 
            extractor_config: ExtractorConfig
    ) -> PdfContext:
        """Initialize all backend PDF objects safely and return a populated PdfContext."""
        return PdfContextBuilder().build(
            path=path,
            pdf_plumber_obj=pdf_plumber_obj,
            extractor_config=extractor_config,
        )
