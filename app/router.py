import logging
import time

from fastapi import APIRouter, File, UploadFile

from app.schemas import CompareResponse
from app.services.ai_summary import summarize_compare_result
from app.services.comparator import compare_pages
from app.services.pdf_reader import extract_pdf_pages_text

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/compare-pdf", response_model=CompareResponse)
async def compare_pdf(
    file_a: UploadFile = File(..., description="First PDF file"),
    file_b: UploadFile = File(..., description="Second PDF file"),
) -> CompareResponse:
    """Compare the visible text content of two PDF files (word-level + optional AI summary)."""
    start = time.perf_counter()

    content_a = await file_a.read()
    content_b = await file_b.read()

    name_a = file_a.filename or "file_a"
    name_b = file_b.filename or "file_b"

    pages_a = extract_pdf_pages_text(content_a, name_a)
    pages_b = extract_pdf_pages_text(content_b, name_b)

    result = compare_pages(pages_a, pages_b)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    ai_summary: str | None = None
    try:
        ai_summary = await summarize_compare_result(result, name_a, name_b)
    except Exception as exc:
        logger.warning("AI summary failed: %s", exc)

    return CompareResponse(
        same=result.same,
        summary=result.summary,
        differences=result.differences,
        elapsed_ms=elapsed_ms,
        ai_summary=ai_summary,
    )
