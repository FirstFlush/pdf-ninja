from ._base import BaseElementExtractor
from ..dataclasses import PdfContext, PdfElement
from pdfplumber.page import Page


class TextExtractor(BaseElementExtractor):

    def __init__(self, min_font_size: float = 0.0):
        self.min_font_size = min_font_size

    def extract(self, ctx: PdfContext) -> dict[int, list[PdfElement]]:
        if ctx.pdf_plumber is None:
            return {}
        results: dict[int, list[PdfElement]] = {}
        
        for i, page in enumerate(ctx.pdf_plumber.pages, start=1):
            elements = self._extract_page_text(page, page_number=i)
            if elements:
                results[i] = elements
                
        return results
    
    def _extract_page_text(self, page: Page, page_number: int) -> list[PdfElement]:
        words = page.extract_words(x_tolerance=1, y_tolerance=3)
        elements: list[PdfElement] = []

        for w in words:
            text = w.get("text", "").strip()
            if not text:
                continue
            font_size = w.get("size", None)
            if font_size and font_size < self.min_font_size:
                continue
            bbox = [w["x0"], w["top"], w["x1"], w["bottom"]]

            elements.append(
                PdfElement(
                    type="text",
                    page=page_number,
                    content=text,
                    bbox=bbox,
                    font_size=font_size,
                    font_name=w.get("fontname"),
                    meta={"source": "pdfplumber"},
                )
            )

        return elements