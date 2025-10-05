from pathlib import Path
from pypdf import PdfReader
from typing import Any


class MetadataExtractor:
    
    def extract_metadata(self, path: Path, pdf_reader: PdfReader) -> dict[str, Any]:
        
        reader_meta = pdf_reader.metadata or {}
        meta = {
            "title": reader_meta.get("/Title"),
            "author": reader_meta.get("/Author"),
            "creator": reader_meta.get("/Creator"),
            "producer": reader_meta.get("/Producer"),
            "subject": reader_meta.get("/Subject"),
            "keywords": reader_meta.get("/Keywords"),
            "creation_date": self._parse_pdf_date(reader_meta.get("/CreationDate")),
            "mod_date": self._parse_pdf_date(reader_meta.get("/ModDate")),
            "page_count": len(pdf_reader.pages),
            "encrypted": pdf_reader.is_encrypted,
            "pdf_version": getattr(pdf_reader, "pdf_header_version", None),
        }
        
        return {k: v for k, v in meta.items() if v is not None}       

    def _parse_pdf_date(self, value: Any) -> str | None:
        """
        Converts PDF-style date strings like 'D:20230805123000Z' to ISO 8601.
        """
        if not isinstance(value, str) or not value.startswith("D:"):
            return None
        try:
            val = value[2:]
            year = val[0:4]
            month = val[4:6] or "01"
            day = val[6:8] or "01"
            hour = val[8:10] or "00"
            minute = val[10:12] or "00"
            second = val[12:14] or "00"
            return f"{year}-{month}-{day}T{hour}:{minute}:{second}Z"
        except Exception:
            return None