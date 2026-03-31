import time

from fastapi import APIRouter, UploadFile, File

from app.schemas import CompareResponse
from app.services.comparator import compare_pages
from app.services.pdf_reader import extract_pdf_pages_text

router = APIRouter()


@router.post("/compare-pdf", response_model=CompareResponse)
async def compare_pdf(
    file_a: UploadFile = File(..., description="First PDF file"),
    file_b: UploadFile = File(..., description="Second PDF file"),
) -> CompareResponse:
    """Compare the visible text content of two PDF files page-by-page."""
    start = time.perf_counter()

    content_a = await file_a.read()
    content_b = await file_b.read()

    pages_a = extract_pdf_pages_text(content_a, file_a.filename or "file_a")
    pages_b = extract_pdf_pages_text(content_b, file_b.filename or "file_b")

    result = compare_pages(pages_a, pages_b)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    return CompareResponse(
        same=result.same,
        summary=result.summary,
        differences=result.differences,
        elapsed_ms=elapsed_ms,
    )
