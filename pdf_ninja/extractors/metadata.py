from pathlib import Path
from pypdf import PdfReader
from typing import Any


class MetadataExtractor:
    
    def extract_metadata(self, path: Path, pdf_reader: PdfReader) -> dict[str, Any]:
        return {}