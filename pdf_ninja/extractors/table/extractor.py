import logging
from .._base import BaseElementExtractor
from ...dataclasses import PdfContext
from ...types import ElementsByPage
from ._camelot import CamelotExtractor
from ._tabula import TabulaExtractor
from ._postprocessor import TablePostprocessor

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


class TableExtractor(BaseElementExtractor):
    
    def __init__(self):
        self._camelot_extractor = CamelotExtractor()
        self._tabula_extractor = TabulaExtractor()
        self._postprocessor = TablePostprocessor()

    def extract(self, ctx: PdfContext) -> ElementsByPage:
        try:
            return self._extract(ctx)
        except Exception as e:
            raise
        
    def _extract(self, ctx: PdfContext) -> ElementsByPage:
        results = self._camelot_extractor.extract(ctx)
        postprocessed_results = self._postprocessor.process(results)
        
        return postprocessed_results