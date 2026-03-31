from fastapi import HTTPException, status


class PDFError(HTTPException):
    """Base exception for PDF processing errors."""

    def __init__(self, detail: str):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class InvalidPDFError(PDFError):
    """Raised when the uploaded file is not a valid PDF."""

    def __init__(self, filename: str):
        super().__init__(detail=f"File '{filename}' is not a valid PDF.")


class EmptyPDFError(PDFError):
    """Raised when the PDF has no pages or no extractable text."""

    def __init__(self, filename: str):
        super().__init__(detail=f"File '{filename}' is empty or has no pages.")


class PDFReadError(PDFError):
    """Raised when the PDF cannot be read."""

    def __init__(self, filename: str, reason: str):
        super().__init__(detail=f"Cannot read '{filename}': {reason}")
