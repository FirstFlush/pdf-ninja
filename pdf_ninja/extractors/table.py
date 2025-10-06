from ._base import BaseElementExtractor
from ..config.constants import TABLE_MAX_CELL_LEN, TABLE_IOU_THRESHOLD
from ..dataclasses import PdfContext, PdfElement
from ..types import ElementsByPage
from camelot.core import TableList, Table
import logging
from typing import Literal, Optional, TypedDict

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class TableMeta(TypedDict):
    source: Literal["camelot", "tabula"]
    flavor: Literal["lattice", "stream", "unknown"]
    accuracy: Optional[float]                               # Camelot's geometric accuracy score (0–100). Tabula does not provide accuracy score.
    columns_detected: Optional[int]
    rows_detected: Optional[int]
    page_area: Optional[tuple[float, float, float, float]]  # [x0, y0, x1, y1] bounding box on page


class TableExtractor(BaseElementExtractor):
    
    def __init__(self):
        self._camelot_extractor = CamelotExtractor()
        self._tabula_extractor = TabulaExtractor()
    
    def extract(self, ctx: PdfContext) -> ElementsByPage:
        try:
            return self._extract(ctx)
        except Exception as e:
            raise
        
    def _extract(self, ctx: PdfContext) -> ElementsByPage:
        results = self._camelot_extractor.extract(ctx)
        return results


class CamelotExtractor:

    def extract(self, ctx: PdfContext) -> ElementsByPage:
        """
        Convert pre-parsed Camelot TableList into structured PdfElement objects.
        Assumes ctx.camelot_tables has been filled by PdfContext.
        """
        if not ctx.camelot_tables:
            return {}

        lattice = list(ctx.camelot_tables.lattice or [])
        stream = list(ctx.camelot_tables.stream or [])
        combined = TableList(lattice + stream)
        deduplicated = self._dedupe_by_bbox(tables=combined)

        return self._create_elements(deduplicated)
        
    def _create_elements(self, tables: TableList) -> ElementsByPage:
        results: ElementsByPage = {}
        for table in tables:
            try:
                page_num = int(getattr(table, "page", 1))
                bbox = getattr(table, "_bbox", None)
                if not bbox or len(bbox) != 4:
                    continue
                x0, y0, x1, y1 = bbox

                # Normalize table cells: strip text and convert blanks to None
                raw_rows = table.df.values.tolist()
                rows = [
                    [cell.strip() if isinstance(cell, str) and cell.strip() else None for cell in row]
                    for row in raw_rows
                ]

                if any(cell and len(cell) > TABLE_MAX_CELL_LEN for row in rows for cell in row):
                    continue
                
                meta: TableMeta = {
                    "source": "camelot",
                    "flavor": getattr(table, "flavor", "unknown"),
                    "accuracy": getattr(table, "accuracy", None),
                    "columns_detected": table.shape[1] if hasattr(table, "shape") else None,
                    "rows_detected": table.shape[0] if hasattr(table, "shape") else None,
                    "page_area": (x0, y0, x1, y1),
                }

                element = PdfElement(
                    type="table",
                    page=page_num,
                    rows=rows,
                    bbox=[x0, y0, x1, y1],
                    meta=dict(meta),
                )
                results.setdefault(page_num, []).append(element)

            except Exception:
                # Skip this table if it’s malformed, but don’t break extraction
                continue

        return results

    def _dedupe_by_bbox(self, tables: TableList) -> TableList:
        unique: list[Table] = []

        for t in tables:
            # Skip tables with missing bbox
            if not getattr(t, "_bbox", None):
                continue

            # check if overlaps with an existing one
            duplicate_index: int | None = None
            for i, u in enumerate(unique):
                if self._iou(t._bbox, u._bbox) > TABLE_IOU_THRESHOLD:
                    duplicate_index = i
                    break

            if duplicate_index is None:
                # no overlap → keep
                unique.append(t)
            else:
                # overlap found — decide which to keep
                current = unique[duplicate_index]
                # prefer stream over lattice
                if getattr(t, "flavor", "") == "stream" and getattr(current, "flavor", "") == "lattice":
                    unique[duplicate_index] = t
                # otherwise, keep existing
                else:
                    continue

        return TableList(unique)


    def _iou(
            self, 
            b1: tuple[float, float, float, float] | None, 
            b2: tuple[float, float, float, float]| None
    ) -> float:
        if not b1 or not b2:
            return 0
        x0 = max(b1[0], b2[0])
        y0 = max(b1[1], b2[1])
        x1 = min(b1[2], b2[2])
        y1 = min(b1[3], b2[3])
        inter_area = max(0, x1 - x0) * max(0, y1 - y0)
        b1_area = (b1[2] - b1[0]) * (b1[3] - b1[1])
        b2_area = (b2[2] - b2[0]) * (b2[3] - b2[1])
        union_area = b1_area + b2_area - inter_area
        return inter_area / union_area if union_area else 0


class TabulaExtractor:
        
    def extract(self, ctx: PdfContext) -> ElementsByPage:
        raise NotImplementedError("Tabular table extraction not yet implemented")
        