from .._base import BaseElementExtractor
from ...dataclasses import PdfContext


class ImageExtractor(BaseElementExtractor):
    
    def extract(self, ctx: PdfContext):
        ...