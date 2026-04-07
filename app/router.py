import logging
import time

from fastapi import APIRouter, File, Query, UploadFile

from app.schemas import (
    CompareAuditHistoryResponse,
    CompareAuditItem,
    CompareResponse,
    SharePointCompareRequest,
    SharePointListFilesRequest,
    SharePointListFilesResponse,
    SignatureCompareRequest,
    SignatureCompareResponse,
    SignatureInfo,
)
from app.services.ai_summary import summarize_compare_result
from app.services.audit_service import (
    get_compare_history,
    write_compare_db,
    write_compare_log,
)
from app.services.comparator import compare_pages
from app.services.pdf_signature import detect_digital_signatures
from app.services.pdf_reader import extract_pdf_pages_text
from app.services.sharepoint_client import (
    download_sharepoint_file,
    list_sharepoint_files,
    validate_sharepoint_compare_paths,
    validate_sharepoint_folder_listing,
)
from app.services.signature_compare import compare_signatures_base64

logger = logging.getLogger(__name__)

router = APIRouter()


def _sharepoint_list_files_response(
    folder_location: str,
    web_url: str | None,
    typefile: str,
    strict_folder_rules: bool,
) -> SharePointListFilesResponse:
    files = list_sharepoint_files(
        folder_location=folder_location,
        web_url=web_url,
        typefile=typefile,
    )
    if strict_folder_rules:
        files = validate_sharepoint_folder_listing(files)
    return SharePointListFilesResponse(files=files)


async def _build_compare_response(
    content_a: bytes, content_b: bytes, name_a: str, name_b: str
) -> CompareResponse:
    start = time.perf_counter()

    pages_a = extract_pdf_pages_text(content_a, name_a)
    pages_b = extract_pdf_pages_text(content_b, name_b)

    sig_a = detect_digital_signatures(content_a)
    sig_b = detect_digital_signatures(content_b)

    result = compare_pages(pages_a, pages_b)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

    ai_summary: str | None = None
    try:
        ai_summary = await summarize_compare_result(result, name_a, name_b)
    except Exception as exc:
        logger.warning("AI summary failed: %s", exc)

    response = CompareResponse(
        same=result.same,
        summary=result.summary,
        differences=result.differences,
        source_file=name_a,
        target_file=name_b,
        source_signature=SignatureInfo(**sig_a),
        target_signature=SignatureInfo(**sig_b),
        elapsed_ms=elapsed_ms,
        ai_summary=ai_summary,
    )

    # Persist audit before returning response to client.
    try:
        write_compare_log(response)
    except Exception as exc:
        logger.warning("Write compare log failed: %s", exc)

    try:
        write_compare_db(response)
    except Exception as exc:
        logger.warning("Write compare DB failed: %s", exc)

    return response


@router.post("/compare-pdf", response_model=CompareResponse)
async def compare_pdf(
    file_a: UploadFile = File(..., description="First PDF file"),
    file_b: UploadFile = File(..., description="Second PDF file"),
) -> CompareResponse:
    """Compare the visible text content of two PDF files (word-level + optional AI summary)."""
    content_a = await file_a.read()
    content_b = await file_b.read()
    name_a = file_a.filename or "file_a"
    name_b = file_b.filename or "file_b"
    return await _build_compare_response(
        content_a=content_a,
        content_b=content_b,
        name_a=name_a,
        name_b=name_b,
    )


@router.post("/compare-pdf-sharepoint", response_model=CompareResponse)
async def compare_pdf_sharepoint(req: SharePointCompareRequest) -> CompareResponse:
    """Download two PDFs from SharePoint, then compare visible text content."""
    validate_sharepoint_compare_paths(req.location_a, req.location_b)
    content_a = download_sharepoint_file(
        location=req.location_a, web_url=req.web_url, fetch_mode=req.fetch_mode
    )
    content_b = download_sharepoint_file(
        location=req.location_b, web_url=req.web_url, fetch_mode=req.fetch_mode
    )

    name_a = req.location_a.split("/")[-1] or "sharepoint_file_a"
    name_b = req.location_b.split("/")[-1] or "sharepoint_file_b"

    return await _build_compare_response(
        content_a=content_a,
        content_b=content_b,
        name_a=name_a,
        name_b=name_b,
    )


@router.get(
    "/sharepoint/list-files",
    response_model=SharePointListFilesResponse,
    summary="Liệt kê file trong folder SharePoint (GET)",
    description=(
        "Cùng logic với POST; dùng query string (phù hợp thao tác chỉ đọc). "
        "`folder_location` cần encode URL nếu có ký tự đặc biệt."
    ),
)
async def sharepoint_list_files_get(
    folder_location: str = Query(..., description="Đường dẫn folder trong site."),
    web_url: str | None = Query(None, description="Site URL; bỏ trống dùng .env."),
    typefile: str = Query("pdf", description="Tham số lọc gửi Power Automate."),
    strict_folder_rules: bool = Query(
        True,
        description="True: 1–2 PDF, không file khác .pdf. False: danh sách gốc từ PA.",
    ),
) -> SharePointListFilesResponse:
    return _sharepoint_list_files_response(
        folder_location=folder_location,
        web_url=web_url,
        typefile=typefile,
        strict_folder_rules=strict_folder_rules,
    )


@router.post(
    "/sharepoint/list-files",
    response_model=SharePointListFilesResponse,
    summary="Liệt kê file trong folder SharePoint (POST)",
    description=(
        "Giữ POST để gửi JSON body (đường folder dài, nhiều field) — không phụ thuộc GET body. "
        "Mặc định áp quy tắc 1–2 file PDF (strict_folder_rules=true); "
        "đặt false để nhận toàn bộ danh sách PA. Xem thêm GET cùng path."
    ),
)
async def sharepoint_list_files_post(
    req: SharePointListFilesRequest,
) -> SharePointListFilesResponse:
    return _sharepoint_list_files_response(
        folder_location=req.folder_location,
        web_url=req.web_url,
        typefile=req.typefile,
        strict_folder_rules=req.strict_folder_rules,
    )


@router.get("/audit-history", response_model=CompareAuditHistoryResponse)
async def audit_history(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> CompareAuditHistoryResponse:
    total, rows = get_compare_history(limit=limit, offset=offset)
    items = [
        CompareAuditItem(
            id=row.id,
            source_file=row.source_file,
            target_file=row.target_file,
            same=row.same,
            total_differences=row.total_differences,
            elapsed_ms=row.elapsed_ms,
            created_at=row.created_at,
        )
        for row in rows
    ]
    return CompareAuditHistoryResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=items,
    )


@router.post(
    "/signature_compare",
    response_model=SignatureCompareResponse,
    summary="So sánh 2 ảnh chữ ký (PoC simple)",
)
async def signature_compare(req: SignatureCompareRequest) -> SignatureCompareResponse:
    """
    Step 1 PoC:
    - input: 2 base64 signature images
    - output: final score + components (overlap/shape/projection) + decision
    """
    try:
        result = compare_signatures_base64(
            signature_ref=req.signature_ref,
            signature_test=req.signature_test,
        )
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return SignatureCompareResponse(**result)
