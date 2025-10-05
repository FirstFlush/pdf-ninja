from ._base import BaseExtractor
from ..dataclasses import PdfContext


class TableExtractor(BaseExtractor):
    
    def extract(self, ctx: PdfContext):
        ...