from ._base import BaseExtractor
from ..dataclasses import PdfContext


class FigureExtractor(BaseExtractor):
    
    def extract(self, ctx: PdfContext):
        ...