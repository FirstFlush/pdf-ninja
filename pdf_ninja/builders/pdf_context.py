from camelot.core import TableList
from camelot.io import read_pdf as read_pdf_camelot
import logging
from pathlib import Path
from tabula.io import read_pdf as read_pdf_tabula
from tabula.errors import JavaNotFoundError
from typing import Any, cast
import pdfplumber
from pypdf import PdfReader
from ..dataclasses import PdfContext
from ..exc import PdfNinjaParsingError
from ..types import ExtractorConfig

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class PdfContextBuilder:
    
    def build(
            self, 
            path: Path, 
            pdf_plumber_obj: pdfplumber.pdf.PDF, 
            extractor_config: ExtractorConfig | None = None
    ) -> PdfContext:
        if not extractor_config:
            extractor_config = {}
        return PdfContext(
            pdf_plumber=pdf_plumber_obj,
            camelot_tables = self._camelot(path, config=extractor_config.get("camelot", {})),
            pypdf_reader = self._pypdf(path, config=extractor_config.get("pypdf", {})),
            tabula_tables = self._tabula(path, config=extractor_config.get("tabula", {})),
        )

    def _camelot(self, path: Path, config: dict[str, Any]) -> TableList:
        try:
            return read_pdf_camelot(str(path), pages="all", flavor="hybrid", **config)
        except (OSError, ValueError) as e:
            raise PdfNinjaParsingError(f"Camelot I/O error for {path.name}: {e}") from e

        except Exception as e:
            raise PdfNinjaParsingError(f"Camelot failed to parse {path.name}: {e}") from e

    def _pypdf(self, path: Path, config: dict[str, Any]) -> PdfReader:
        try:
            return PdfReader(str(path), **config)
        except OSError as e:
            raise PdfNinjaParsingError(f"Cannot open file {path.name}: {e}") from e
        except Exception as e:
            raise PdfNinjaParsingError(f"pypdf failed to read structure of {path.name}: {e}") from e

    def _tabula(self, path: Path, config: dict[str, Any]) -> dict[str, Any]:
        output_format = config.get("output_format")
        if output_format and output_format != "json":
            logger.debug(f"Overriding Tabula config output_format value `{output_format}`. PdfNinja requires `json`")
        config["output_format"] = "json"
        try:
            raw = read_pdf_tabula(str(path), pages="all", **config)
            return cast(dict[str, Any], raw)

        except JavaNotFoundError as e:
            raise PdfNinjaParsingError(
                f"Tabula requires Java (not found) when parsing {path.name}: {e}"
            ) from e
        except (OSError, ValueError) as e:
            raise PdfNinjaParsingError(f"Tabula I/O error for {path.name}: {e}") from e
        except Exception as e:
            raise PdfNinjaParsingError(f"Tabula failed to parse {path.name}: {e}") from e
