from ._base import BaseExtractor
from ..dataclasses import PdfContext


class ImageExtractor(BaseExtractor):
    
    def extract(self, ctx: PdfContext):
        ...