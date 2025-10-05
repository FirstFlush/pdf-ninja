from typing import Any, TypedDict
from typing_extensions import NotRequired


class ExtractorConfig(TypedDict, total=False):
    
    camelot: NotRequired[dict[str, Any]]
    pdf_plumber: NotRequired[dict[str, Any]]
    pypdf: NotRequired[dict[str, Any]]
    tabula: NotRequired[dict[str, Any]]
    