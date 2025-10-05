from camelot.core import TableList
from dataclasses import dataclass, field
from pdfplumber.pdf import PDF
from pypdf import PdfReader
from typing import Any, Optional, Literal

ElementType = Literal["text", "table", "image", "figure"]


@dataclass
class PdfContext:

    pypdf_reader: PdfReader    
    pdf_plumber: Optional[PDF] = None
    camelot_tables: Optional[TableList] = None
    tabula_tables: Optional[dict[str, Any]] = None


@dataclass
class ExtractedElements:
    text: Optional[dict[int, list["PdfElement"]]] = field(default_factory=dict)
    tables: Optional[dict[int, list["PdfElement"]]] = field(default_factory=dict)
    images: Optional[dict[int, list["PdfElement"]]] = field(default_factory=dict)
    figures: Optional[dict[int, list["PdfElement"]]] = field(default_factory=dict)
    meta: dict[str, Any] = field(default_factory=dict)
   
    
@dataclass
class PdfElement:
    """
    Represents a single piece of content on a page — text block, table, image, or figure.
    """
    type: ElementType
    page: int
    order: int = field(default=-1)              # set downstream when PdfPage is being built
    content: Optional[str] = None               # Used for text or textified tables
    rows: Optional[list[list[str]]] = None      # Used for structured tables
    bbox: Optional[list[float]] = None          # [x0, y0, x1, y1]
    font_size: Optional[float] = None
    font_name: Optional[str] = None
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class PdfPage:
    """
    Represents a single page of a PDF, containing multiple elements in reading order.
    """
    page_number: int
    elements: list[PdfElement] = field(default_factory=list)

    def stringify(
            self,
            include_tables: bool = True,
            include_images: bool = False
    ) -> str:
        """
        Returns the page’s text content as a flattened string in reading order.
        Tables can be optionally included as textified rows.
        Images and figures are skipped by default.
        """
        lines = []
        for el in sorted(self.elements, key=lambda e: e.order):
            if el.type == "text":
                lines.append(el.content or "")
            elif el.type == "table" and include_tables:
                if el.rows:
                    rows_as_text = [" | ".join(r) for r in el.rows]
                    lines.append("\n".join(rows_as_text))
                elif el.content:
                    lines.append(el.content)
            elif el.type in ("image", "figure") and include_images:
                caption = el.meta.get("caption")
                if caption:
                    lines.append(f"[Image: {caption}]")
        return "\n\n".join(lines).strip()


@dataclass
class ParsedPdf:
    """
    Represents a fully parsed PDF document, including metadata and all pages.
    """
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    pages: list[PdfPage] = field(default_factory=list)

    def stringify(
        self,
        include_tables: bool = True,
        include_images: bool = False
    ) -> str:
        """
        Returns the entire document as a single concatenated text string,
        in page and element order.
        """
        page_texts = [
            page.stringify(include_tables=include_tables, include_images=include_images)
            for page in sorted(self.pages, key=lambda p: p.page_number)
        ]
        return "\n\n--- PAGE BREAK ---\n\n".join(filter(None, page_texts))

    def to_dict(self) -> dict:
        """
        Converts the ParsedPdf into a serializable dictionary.
        """
        return {
            "source": self.source,
            "metadata": self.metadata,
            "pages": [
                {
                    "page_number": p.page_number,
                    "elements": [vars(e) for e in p.elements]
                }
                for p in self.pages
            ],
        }
