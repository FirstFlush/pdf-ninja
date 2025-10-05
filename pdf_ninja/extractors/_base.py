from abc import ABC, abstractmethod
from typing import Any
from ..dataclasses import PdfContext

class BaseElementExtractor(ABC):
    
    @abstractmethod
    def extract(self, ctx: PdfContext) -> Any:
        pass