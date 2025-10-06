from __future__ import annotations
import logging
import re
from dataclasses import replace
from typing import Iterable, List, Tuple, Dict, Any, Callable

import numpy as np
import pandas as pd

from ...dataclasses import PdfElement
from ...types import ElementsByPage

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


_NUMERIC_RE = re.compile(r"""
    ^\s*                # leading space
    [\(\+\-]?           # sign or parentheses
    (?:
        \d{1,3}         # 1-3 digits
        (?:[, ]\d{3})*  # optional thousands groups
        |\d+            # or just digits
    )
    (?:\.\d+)?          # optional decimal
    (?:\s?[%$A-Za-z]*)? # optional units/symbols (%, $, USD, lb, etc.)
    \s*$
""", re.X)

_HEADER_TOKEN_HINTS = re.compile(
    r"(year|quarter|three|months|ended|notes?|highlights?|currency|usd|cad|unaudited|audited)",
    re.I,
)

class TablePostprocessor:
    """
    Structural cleanup for Camelot-extracted tables embedded in PdfElement.meta["_camelot_table"].

    Pipeline:
      1) normalize dataframe cells (strip newlines/whitespace)
      2) compute row features (numeric_ratio, header_likelihood)
      3) detect header block (possibly multi-row), collapse into a single header row
      4) split into logical subtables on (a) reappearing header-like rows, (b) large vertical gaps
      5) recompute bbox per subtable via geometry from table.cells
    """

    def __init__(
        self,
        # header detection
        min_cols_for_header: int = 2,
        numeric_ratio_header_max: float = 0.35,
        header_token_boost: float = 0.15,
        # splitting
        gap_multiplier: float = 1.6,   # > median_gap * multiplier => split
        reheader_allow_numeric_ratio_max: float = 0.5,
    ):
        self.min_cols_for_header = min_cols_for_header
        self.numeric_ratio_header_max = numeric_ratio_header_max
        self.header_token_boost = header_token_boost
        self.gap_multiplier = gap_multiplier
        self.reheader_allow_numeric_ratio_max = reheader_allow_numeric_ratio_max

    def process(self, elements_by_page: ElementsByPage) -> ElementsByPage:
        return elements_by_page
        
    def _process(self, elements_by_page: ElementsByPage) -> ElementsByPage:
        processed: ElementsByPage = {}

        for page_num, elements in elements_by_page.items():
            out: list[PdfElement] = []
            for elem in elements:
                if elem.type != "table":
                    out.append(elem)
                    continue

                try:
                    cleaned = self._process_one(elem)
                    out.extend(cleaned)
                except Exception as e:
                    logger.debug(f"[postprocess] p{page_num} table failed: {type(e).__name__}: {e}")
                    out.append(elem)

            processed[page_num] = out

        return processed

    def _process_one(self, elem: PdfElement) -> list[PdfElement]:
        table = elem.meta.get("_camelot_table")
        df: pd.DataFrame | None = getattr(table, "df", None)
        cells: list[Any] | None = getattr(table, "cells", None)
        if df is None or cells is None:
            return [elem]  # nothing to do

        df = self._normalize_df(df)

        # features by row
        numeric_mask = df.apply(lambda s: s.map(self._is_numeric_like))
        nonempty_mask = df.apply(lambda s: s.map(self._is_nonempty))
        header_mask = df.apply(lambda s: s.map(self._has_header_tokens))
        numeric_ratio = numeric_mask.mean(axis=1).to_numpy()
        nonempty_ratio = nonempty_mask.mean(axis=1).to_numpy()
        header_hint = header_mask.any(axis=1).to_numpy()
        # numeric_ratio = df.applymap(self._is_numeric_like).mean(axis=1).to_numpy()
        # nonempty_ratio = df.applymap(self._is_nonempty).mean(axis=1).to_numpy()
        # header_hint = df.applymap(self._has_header_tokens).any(axis=1).to_numpy()

        # header score: prefer non-numeric, non-empty, token-hinted rows
        header_score = (1 - numeric_ratio) * nonempty_ratio + header_hint.astype(float) * self.header_token_boost

        # locate top header block
        header_rows = self._detect_header_block(df, header_score, numeric_ratio)
        header_row_idx = list(header_rows)

        # collapse header rows into a single header (join cells with space)
        df, header = self._collapse_header(df, header_row_idx)

        # split points: reappearing headers or large vertical gaps
        row_positions = self._row_positions(cells)  # top->bottom positions
        gaps = self._row_gaps(row_positions)

        split_points = set()
        # reheader: rows that look like header again later
        reheader_idx = self._detect_reheader_rows(df, numeric_ratio, nonempty_ratio, header)
        split_points.update(reheader_idx)

        # large gaps
        if len(gaps) > 0:
            median_gap = float(np.median(gaps))
            for i, g in enumerate(gaps):
                if g > median_gap * self.gap_multiplier:
                    split_points.add(i + 1)  # split starts at next row

        # always ensure we start after header block
        start_row = max(header_row_idx[-1] + 1, 0) if header_row_idx else 0
        split_points = sorted([i for i in split_points if i >= start_row])

        chunks = self._slice_chunks(df, start_row, split_points)

        # build PdfElements per chunk with recomputed bbox
        results: list[PdfElement] = []
        for chunk in chunks:
            if chunk.empty:
                continue
            bbox = self._bbox_for_rows(cells, set(chunk.index))
            # preserve meta but record lineage
            meta = dict(elem.meta)
            meta["split_from"] = meta.get("id", meta.get("split_from"))
            meta["header"] = header  # keep resolved header for downstream
            rows = [header] + chunk.values.tolist() if header else chunk.values.tolist()

            sub = replace(
                elem,
                rows=rows,
                bbox=list(bbox),
                meta=meta,
            )
            results.append(sub)

        return results or [elem]

    @staticmethod
    def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
        def norm(x: Any) -> str:
            if x is None or (isinstance(x, float) and np.isnan(x)):
                return ""
            s = str(x).replace("\r", " ").replace("\n", " ").strip()
            return re.sub(r"\s{2,}", " ", s)

        # Pylance-safe: map per column
        return df.apply(lambda s: s.map(norm))

    @staticmethod
    def _is_nonempty(x: str) -> bool:
        return bool(x and x.strip())

    @staticmethod
    def _is_numeric_like(x: str) -> bool:
        if not x or not x.strip():
            return False
        return bool(_NUMERIC_RE.match(x))

    @staticmethod
    def _has_header_tokens(x: str) -> bool:
        if not x:
            return False
        return bool(_HEADER_TOKEN_HINTS.search(x))

    def _detect_header_block(
        self,
        df: pd.DataFrame,
        header_score: np.ndarray,
        numeric_ratio: np.ndarray,
    ) -> Iterable[int]:
        """
        Heuristic:
          - scan from top while header_score is high and numeric_ratio is low
          - require at least `min_cols_for_header` non-empty cells in a row
          - stop once we hit a clearly data-like row (numeric_ratio >= ~0.5)
        """
        rows: list[int] = []
        for i in range(len(df)):
            row = df.iloc[i]
            nonempty_cols = int(row.apply(self._is_nonempty).sum())
            if nonempty_cols < self.min_cols_for_header:
                # allow title/preamble lines to be part of header block if followed by header-ish lines
                if rows:
                    rows.append(i)
                else:
                    continue
            else:
                if numeric_ratio[i] <= self.numeric_ratio_header_max or header_score[i] >= 0.6:
                    rows.append(i)
                else:
                    break

        # trim trailing fully empty rows
        while rows and not df.iloc[rows[-1]].apply(self._is_nonempty).any():
            rows.pop()

        return rows

    @staticmethod
    def _collapse_header(df: pd.DataFrame, header_rows: List[int]) -> tuple[pd.DataFrame, list[str] | None]:
        if not header_rows:
            return df, None
        header_df = df.iloc[header_rows, :]
        # join vertical header fragments per column
        header = [
            " ".join([str(v) for v in header_df[col].tolist() if v and str(v).strip()])
            .strip()
            for col in header_df.columns
        ]
        # drop header rows from df body
        mask = np.ones(len(df), dtype=bool)
        mask[header_rows] = False
        body = df.iloc[mask, :]
        return body, header

    @staticmethod
    def _row_positions(cells: list[Any]) -> list[float]:
        """
        Compute row baselines (average of y1 for each row index).
        Camelot's cell has attributes: row, col, x1, y1, x2, y2 (top-left is (x1, y2)).
        """
        rows: Dict[int, list[float]] = {}
        for c in cells:
            rows.setdefault(c.row, []).append(c.y1)  # using y1 (lower y) is consistent for gaps
        # rows are 0..N-1; map to average y
        return [float(np.mean(rows[i])) for i in sorted(rows.keys())]

    @staticmethod
    def _row_gaps(row_positions: list[float]) -> list[float]:
        # gaps between consecutive rows (positive if well-separated vertically)
        if len(row_positions) <= 1:
            return []
        return [abs(row_positions[i] - row_positions[i + 1]) for i in range(len(row_positions) - 1)]

    def _detect_reheader_rows(
        self,
        df: pd.DataFrame,
        numeric_ratio: np.ndarray,
        nonempty_ratio: np.ndarray,
        header: list[str] | None,
    ) -> List[int]:
        """
        Identify rows later in the table that look like a header line, used to split.
        We’re conservative: low numeric ratio, decent non-empty coverage, and optionally
        shares tokens with the resolved header.
        """
        if len(df) == 0:
            return []

        header_tokens = set()
        if header:
            for h in header:
                header_tokens.update(self._tokenize(h))

        idxs: list[int] = []
        for i in range(len(df)):
            # skip rows that are too numeric to be header
            if numeric_ratio[i] > self.reheader_allow_numeric_ratio_max:
                continue
            if nonempty_ratio[i] < 0.4:
                continue

            if header_tokens:
                row_tokens = set()
                for v in df.iloc[i].tolist():
                    row_tokens.update(self._tokenize(v))
                # modest overlap is enough
                if self._jaccard(row_tokens, header_tokens) >= 0.2:
                    idxs.append(i)
                else:
                    # still allow explicit header hints
                    if df.iloc[i].apply(self._has_header_tokens).any():
                        idxs.append(i)
            else:
                if df.iloc[i].apply(self._has_header_tokens).any():
                    idxs.append(i)
        # de-duplicate consecutive indices
        dedup: list[int] = []
        for i in idxs:
            if not dedup or i != dedup[-1] + 1:
                dedup.append(i)
        return dedup

    @staticmethod
    def _slice_chunks(df: pd.DataFrame, start_row: int, split_points: List[int]) -> List[pd.DataFrame]:
        stops = list(split_points) + [len(df)]
        chunks: list[pd.DataFrame] = []
        cur = start_row
        for s in stops:
            if s <= cur:
                continue
            chunks.append(df.iloc[cur:s, :])
            cur = s
        return chunks

    @staticmethod
    def _bbox_for_rows(cells: list[Any], row_indices: set[int]) -> Tuple[float, float, float, float]:
        sel = [c for c in cells if c.row in row_indices]
        if not sel:
            # fallback to everything
            sel = cells
        x0 = min(c.x1 for c in sel)
        y0 = min(c.y1 for c in sel)
        x1 = max(c.x2 for c in sel)
        y1 = max(c.y2 for c in sel)
        return (x0, y0, x1, y1)

    @staticmethod
    def _tokenize(s: str) -> List[str]:
        if not s:
            return []
        return re.findall(r"[A-Za-z0-9%$]+", s.lower())

    @staticmethod
    def _jaccard(a: set[str], b: set[str]) -> float:
        if not a or not b:
            return 0.0
        inter = len(a & b)
        union = len(a | b)
        return inter / union if union else 0.0
