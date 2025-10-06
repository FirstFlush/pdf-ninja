from ._base import BaseElementExtractor
from ..dataclasses import PdfContext, PdfElement
from ..types import ElementsByPage
from pdfplumber.page import Page
from typing import Any


class TextExtractor(BaseElementExtractor):

    def __init__(self, min_font_size: float = 0.0):
        self.min_font_size = min_font_size

    def extract(self, ctx: PdfContext) -> ElementsByPage:
        if ctx.pdf_plumber is None:
            return {}

        results: ElementsByPage = {}

        for i, page in enumerate(ctx.pdf_plumber.pages, start=1):
            elements = self._extract_page_text(page, page_number=i)
            if elements:
                results[i] = elements

        return results

    def _extract_page_text(self, page: Page, page_number: int) -> list[PdfElement]:
        words = page.extract_words(x_tolerance=2, y_tolerance=4)
        if not words:
            return []

        words.sort(key=lambda w: (w["top"], w["x0"]))

        line_groups = self._group_words_into_lines(words, y_tolerance=4.0)

        line_elements: list[PdfElement] = []
        for line_words in line_groups:
            text = " ".join(w["text"].strip() for w in line_words if w.get("text"))
            if not text:
                continue

            font_size = line_words[0].get("size")
            if font_size and font_size < self.min_font_size:
                continue

            x0 = min(w["x0"] for w in line_words)
            x1 = max(w["x1"] for w in line_words)
            top = min(w["top"] for w in line_words)
            bottom = max(w["bottom"] for w in line_words)
            bbox = [x0, top, x1, bottom]

            line_elements.append(
                PdfElement(
                    type="text",
                    page=page_number,
                    content=text,
                    bbox=bbox,
                    font_size=font_size,
                    font_name=line_words[0].get("fontname"),
                    meta={"source": "pdfplumber"},
                )
            )

        block_elements = self._group_lines_into_blocks(line_elements, y_gap=8.0)

        return block_elements

    def _group_words_into_lines(
        self, words: list[dict[str, Any]], y_tolerance: float = 3.0
    ) -> list[list[dict[str, Any]]]:
        """Group words that share similar vertical 'top' coordinate."""
        if not words:
            return []

        lines: list[list[dict[str, Any]]] = []
        current_line: list[dict[str, Any]] = []
        current_y: float | None = None

        for w in words:
            if current_y is None:
                current_y = w["top"]
                current_line = [w]
                continue

            if abs(w["top"] - current_y) <= y_tolerance:
                current_line.append(w)
            else:
                lines.append(current_line)
                current_line = [w]
                current_y = w["top"]

        if current_line:
            lines.append(current_line)

        return lines

    # ------------------------------------------------------------------

    def _group_lines_into_blocks(
        self, lines: list[PdfElement], y_gap: float = 8.0
    ) -> list[PdfElement]:
        """
        Merge consecutive line elements into paragraph-like text blocks
        if they are close vertically and share similar style.
        """
        if not lines:
            return []

        blocks: list[list[PdfElement]] = []
        current_block: list[PdfElement] = [lines[0]]

        for prev, curr in zip(lines, lines[1:]):
            if not (prev.bbox and curr.bbox):
                continue

            vertical_gap = curr.bbox[1] - prev.bbox[3]
            same_style = (
                prev.font_name == curr.font_name
                and abs((prev.font_size or 0) - (curr.font_size or 0)) < 0.5
            )

            # If lines are close and same style → same block
            if vertical_gap <= y_gap and same_style:
                current_block.append(curr)
            else:
                blocks.append(current_block)
                current_block = [curr]

        if current_block:
            blocks.append(current_block)

        # Merge grouped lines into new block elements
        merged_blocks: list[PdfElement] = []
        for group in blocks:
            merged_blocks.append(self._merge_block(group))

        return merged_blocks

    def _merge_block(self, lines: list[PdfElement]) -> PdfElement:
        """Combine multiple line elements into one text block element."""
        text = " ".join(l.content.strip() for l in lines if l.content)
        x0 = min(l.bbox[0] for l in lines if l.bbox)
        x1 = max(l.bbox[2] for l in lines if l.bbox)
        y0 = min(l.bbox[1] for l in lines if l.bbox)
        y1 = max(l.bbox[3] for l in lines if l.bbox)

        base = lines[0]
        return PdfElement(
            type="text",
            page=base.page,
            content=text,
            bbox=[x0, y0, x1, y1],
            font_size=base.font_size,
            font_name=base.font_name,
            meta={**base.meta, "merged_lines": len(lines)},
        )
