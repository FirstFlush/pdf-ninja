from ...dataclasses import PdfContext
from ...types import ElementsByPage

class TabulaExtractor:
        
    def extract(self, ctx: PdfContext) -> ElementsByPage:
        raise NotImplementedError("Tabular table extraction not yet implemented")
        