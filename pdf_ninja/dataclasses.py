from dataclasses import dataclass
from typing import Any, Optional
from camelot.core import TableList
from pdfplumber.pdf import PDF
from pypdf import PdfReader


@dataclass
class PdfContext:
    
    pdf_plumber: Optional[PDF] = None
    camelot_tables: Optional[TableList] = None
    tabula_tables: Optional[dict[str, Any]] = None
    pypdf_reader: Optional[PdfReader] = None
