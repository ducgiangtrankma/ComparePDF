import fitz  # PyMuPDF

from app.exceptions import EmptyPDFError, InvalidPDFError, PDFReadError


def extract_pdf_pages_text(content: bytes, filename: str) -> list[str]:
    """Extract text from each page of a PDF file.

    Returns a list where each element is the full text of one page.
    """
    try:
        doc = fitz.open(stream=content, filetype="pdf")
    except Exception as exc:
        raise InvalidPDFError(filename) from exc

    if doc.page_count == 0:
        doc.close()
        raise EmptyPDFError(filename)

    try:
        pages = [page.get_text("text") for page in doc]
    except Exception as exc:
        raise PDFReadError(filename, str(exc)) from exc
    finally:
        doc.close()

    return pages
