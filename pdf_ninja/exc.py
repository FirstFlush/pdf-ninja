
class PdfNinjaError(Exception):
    """Base class for any pdf-ninja custom exceptions"""
    pass

class PdfNinjaParsingError(PdfNinjaError):
    """Raised when any underlying PDF parsing tool fails."""
    pass