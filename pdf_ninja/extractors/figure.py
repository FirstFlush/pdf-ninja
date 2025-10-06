from ._base import BaseElementExtractor
from ..dataclasses import PdfContext


class FigureExtractor(BaseElementExtractor):
    
    def extract(self, ctx: PdfContext):
        ...