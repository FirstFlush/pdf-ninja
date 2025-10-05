from ._base import BaseExtractor
from ..dataclasses import PdfContext


class MetadataExtractor(BaseExtractor):
    
    def extract(self, ctx: PdfContext):
        ...