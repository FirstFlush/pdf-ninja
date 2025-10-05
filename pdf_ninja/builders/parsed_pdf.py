from pathlib import Path
from ..dataclasses import ExtractedElements, ParsedPdf, PdfPage, PdfElement


class PdfBuilder:
    
    def __init__(self, path: Path, extracted_elements: ExtractedElements):
        self.extracted = extracted_elements
        self.path = path

    def build_parsed_pdf(self) -> ParsedPdf:
        """
        Assemble a full ParsedPdf object from extracted elements.
        """
        pages: list[PdfPage] = []
        page_map: dict[int, list[PdfElement]] = {}
        for element_dict in [
            self.extracted.text,
            self.extracted.tables,
            self.extracted.images,
            self.extracted.figures,
        ]:
            if not element_dict:
                continue
            for page_num, elements in element_dict.items():
                page_map.setdefault(page_num, []).extend(elements)

        # Sort elements within each page and assign reading order
        for page_num, elements in sorted(page_map.items()):
            sorted_elements = self._sort_elements(elements)
            for order, el in enumerate(sorted_elements):
                el.order = order
            pages.append(PdfPage(page_number=page_num, elements=sorted_elements))

        # Metadata may include title, author, etc.
        metadata = self.extracted.meta or {}

        return ParsedPdf(
            source=metadata.get("source", ""),
            metadata=metadata,
            pages=pages,
        )

    def _sort_elements(self, elements: list[PdfElement]) -> list[PdfElement]:
        """
        Sort page elements roughly in visual reading order:
        top-to-bottom, then left-to-right.
        pdfplumber coordinates increase downward (y grows toward page bottom),
        so sort ascending by y0, then x0.
        """
        sorted_elements = sorted(
            elements,
            key=lambda el: (
                el.bbox[1] if el.bbox else float("inf"),  # top (y0)
                el.bbox[0] if el.bbox else float("inf"),  # left (x0)
            ),
        )
        return sorted_elements
