from typing import Any, TypeAlias, TypedDict
from typing_extensions import NotRequired
from .dataclasses import PdfElement

ElementsByPage: TypeAlias = dict[int, list[PdfElement]]


class ExtractorConfig(TypedDict, total=False):
    
    camelot: NotRequired[dict[str, Any]]
    pdf_plumber: NotRequired[dict[str, Any]]
    pypdf: NotRequired[dict[str, Any]]
    tabula: NotRequired[dict[str, Any]]
    
    
    