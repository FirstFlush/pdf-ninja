from __future__ import annotations
import logging
import numpy as np

from ...dataclasses import PdfElement
from ...types import ElementsByPage

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class TablePostprocessor:
    """
    Performs structural cleanup on extracted table elements.
    Currently:
        - Detects and splits multi-table regions (one Camelot bbox containing multiple grids)
        - Recomputes bounding boxes per subtable
    """

    def __init__(self, iou_threshold: float = 0.6):
        self.iou_threshold = iou_threshold

    # ------------------------------------------------------------
    # public API
    # ------------------------------------------------------------
    def process(self, elements_by_page: ElementsByPage) -> ElementsByPage:
        """
        Iterate through all pages and split multi-part tables.
        """
        processed: ElementsByPage = {}

        for page_num, elements in elements_by_page.items():
            new_elems: list[PdfElement] = []
            for elem in elements:
                if elem.type != "table":
                    new_elems.append(elem)
                    continue

                # Split into subtables if structure changes
                try:
                    splits = self._split_if_multi(elem)
                    new_elems.extend(splits)
                except Exception as e:
                    logger.debug(f"Postprocess skip p{page_num} table: {type(e).__name__} - {e}")
                    new_elems.append(elem)

            processed[page_num] = new_elems

        return processed

    # ------------------------------------------------------------
    # core splitting logic
    # ------------------------------------------------------------
    def _split_if_multi(self, elem: PdfElement) -> list[PdfElement]:
        """
        Detects and splits multi-table regions (one Camelot bbox containing multiple grids)
        into separate PdfElements using row-level geometry.

        Returns a list of one or more PdfElements.
        """
        table = elem.meta.get("_camelot_table")
        if not table or not hasattr(table, "cells"):
            # no raw geometry — can’t safely split
            return [elem]

        row_positions = self._get_row_positions(table)
        if len(row_positions) < 3:
            return [elem]

        # Compute vertical gaps between consecutive rows
        gaps = [row_positions[i] - row_positions[i + 1] for i in range(len(row_positions) - 1)]
        median_gap = np.median(gaps)
        if not median_gap or median_gap <= 0:
            return [elem]

        # find unusually large gaps (likely table breaks)
        split_points = [i + 1 for i, g in enumerate(gaps) if g > median_gap * 1.5]
        if not split_points:
            return [elem]

        # ---- perform the splits using pandas slicing ----
        dfs = []
        start = 0
        for stop in split_points + [len(table.df)]:
            dfs.append(table.df.iloc[start:stop, :])
            start = stop

        results: list[PdfElement] = []

        for df_chunk in dfs:
            if df_chunk.empty:
                continue

            bbox = self._subtable_bbox(table, df_chunk.index)
            sub_elem = PdfElement(
                type="table",
                page=elem.page,
                rows=df_chunk.values.tolist(),
                bbox=list(bbox),
                meta={**elem.meta, "split_from": elem.meta.get("id")},
            )
            results.append(sub_elem)

        return results

    # ------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------
    def _get_row_positions(self, table) -> list[float]:
        rows: dict[int, list[float]] = {}
        for c in getattr(table, "cells", []):
            rows.setdefault(c.row, []).append(c.y1)
        return [sum(v) / len(v) for _, v in sorted(rows.items())]

    def _subtable_bbox(self, table, row_indices) -> tuple[float, float, float, float]:
        cells = [c for c in table.cells if c.row in row_indices]
        x0 = min(c.x1 for c in cells)
        y0 = min(c.y1 for c in cells)
        x1 = max(c.x2 for c in cells)
        y1 = max(c.y2 for c in cells)
        return (x0, y0, x1, y1)
