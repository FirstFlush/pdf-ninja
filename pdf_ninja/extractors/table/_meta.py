from typing import Literal, Optional, TypedDict


class TableMeta(TypedDict):
    source: Literal["camelot", "tabula"]
    flavor: Literal["lattice", "stream", "unknown"]
    accuracy: Optional[float]                               # Camelot's geometric accuracy score (0–100). Tabula does not provide accuracy score.
    columns_detected: Optional[int]
    rows_detected: Optional[int]
    page_area: Optional[tuple[float, float, float, float]]  # [x0, y0, x1, y1] bounding box on page

