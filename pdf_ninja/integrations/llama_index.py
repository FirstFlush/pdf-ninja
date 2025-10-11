from pathlib import Path
from pdf_ninja import PdfNinja
import logging
try:
    from llama_index.core import Document # type: ignore
    from llama_index.core.readers.base import BaseReader # type: ignore
except ImportError as e:
    raise ImportError(
        "PdfNinjaReader requires `llama-index` to be installed. "
        "Install with: pip install pdf-ninja[llamaindex]"
    ) from e

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

class PdfNinjaReader(BaseReader):
    """Custom reader that uses PdfNinja to extract text and metadata from PDFs."""

    def __init__(self, input_dir: Path):
        self.input_dir = Path(input_dir)

    def load_data(self) -> list[Document]:
        docs: list[Document] = []

        for pdf_path in self.input_dir.rglob("*.pdf"):
            try:
                parsed = PdfNinja().parse(pdf_path)
                text = parsed.stringify()
                if not text.strip():
                    continue

                metadata = {
                    "file_path": str(pdf_path),
                    "file_name": pdf_path.name,
                    "page_count": len(parsed.pages),
                }

                docs.append(Document(text=text, metadata=metadata))

            except Exception as e:
                logger.error(f"Failed to parse {pdf_path}: {e}")

        return docs