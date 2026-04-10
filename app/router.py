import logging
import time

from fastapi import APIRouter, File, Query, UploadFile

from app.config import SHAREPOINT_SIGNATURE_LOCATION
from app.schemas import (
    CompareAuditHistoryResponse,
    CompareAuditItem,
    CompareResponse,
    HandSignatureCheckResponse,
    HandSignaturePageResult,
    SharePointCompareRequest,
    SharePointListFilesRequest,
    SharePointListFilesResponse,
    SignatureCompareComponents,
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
from app.services.hand_signature_engine import (
    detect_and_compare_hand_signatures,
    detect_and_compare_hand_signatures_with_ref_bytes,
    detect_and_compare_hand_signatures_with_ref_candidates,
)
from app.services.signature_compare import compare_signatures_base64

logger = logging.getLogger(__name__)

router = APIRouter()
_LOCAL_REF_SIGNATURE_PATH = "localPDF/refSignatures/refSingnature.png"


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
    content_a: bytes,
    content_b: bytes,
    name_a: str,
    name_b: str,
    ref_signature_bytes: bytes | None = None,
    ref_signature_candidates: list[tuple[str, bytes]] | None = None,
) -> CompareResponse:
    start = time.perf_counter()

    pages_a = extract_pdf_pages_text(content_a, name_a)
    pages_b = extract_pdf_pages_text(content_b, name_b)

    sig_a = detect_digital_signatures(content_a)
    sig_b = detect_digital_signatures(content_b)
    hand_a_raw: list[dict] = []
    hand_b_raw: list[dict] = []
    try:
        if ref_signature_candidates is None:
            if ref_signature_bytes is not None:
                ref_signature_candidates = [("default_ref", ref_signature_bytes)]
            else:
                with open(_LOCAL_REF_SIGNATURE_PATH, "rb") as f:
                    ref_signature_candidates = [("default_ref", f.read())]
        hand_params = dict(dpi=180, roi_mode="bottom_then_full", bottom_ratio=0.35)
        hand_a_raw = detect_and_compare_hand_signatures_with_ref_candidates(
            pdf_bytes=content_a,
            ref_candidates=ref_signature_candidates,
            **hand_params,
        )
        hand_b_raw = detect_and_compare_hand_signatures_with_ref_candidates(
            pdf_bytes=content_b,
            ref_candidates=ref_signature_candidates,
            **hand_params,
        )
    except Exception as exc:
        logger.warning("Hand signature compare failed: %s", exc)

    def _to_hand_models(raw_list: list[dict]) -> list[HandSignaturePageResult]:
        out: list[HandSignaturePageResult] = []
        for item in raw_list:
            comps = item.get("components")
            components = (
                SignatureCompareComponents(
                    overlap_score=comps["overlap_score"],
                    shape_score=comps["shape_score"],
                    projection_score=comps["projection_score"],
                )
                if comps
                else None
            )
            out.append(
                HandSignaturePageResult(
                    page=item["page"],
                    has_signature=item["has_signature"],
                    best_score=item["best_score"],
                    decision=item.get("decision"),
                    bbox=tuple(item["bbox"]) if item.get("bbox") else None,
                    components=components,
                    matched_reference=item.get("matched_reference"),
                )
            )
        return out

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
        source_hand_signature=_to_hand_models(hand_a_raw),
        target_hand_signature=_to_hand_models(hand_b_raw),
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


@router.post(
    "/compare-pdf",
    response_model=CompareResponse,
    tags=["compare"],
    summary="So sánh hai PDF (upload)",
    description=(
        "Nhận hai file PDF qua multipart. Trả về diff từng từ, thông tin ký số AcroForm, "
        "kết quả chữ ký tay (so với mẫu mặc định trên server), `elapsed_ms` và `ai_summary` nếu bật AI."
    ),
)
async def compare_pdf(
    file_a: UploadFile = File(..., description="PDF thứ nhất (A / nguồn)."),
    file_b: UploadFile = File(..., description="PDF thứ hai (B / đích)."),
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


@router.post(
    "/compare-pdf-sharepoint",
    response_model=CompareResponse,
    tags=["compare"],
    summary="So sánh hai PDF từ SharePoint",
    description=(
        "Tải hai PDF theo `location_a` / `location_b`. Tùy chọn `signature_location`: file ảnh mẫu "
        "hoặc folder chứa .png/.jpg để so khớp chữ ký tay. Cùng pipeline diff + audit như `/compare-pdf`."
    ),
)
async def compare_pdf_sharepoint(req: SharePointCompareRequest) -> CompareResponse:
    """Download two PDFs from SharePoint, then compare visible text content."""
    validate_sharepoint_compare_paths(req.location_a, req.location_b)
    content_a = download_sharepoint_file(
        location=req.location_a, web_url=req.web_url, fetch_mode=req.fetch_mode
    )
    content_b = download_sharepoint_file(
        location=req.location_b, web_url=req.web_url, fetch_mode=req.fetch_mode
    )
    ref_sig_bytes: bytes | None = None
    ref_sig_candidates: list[tuple[str, bytes]] | None = None
    sig_loc = (req.signature_location or SHAREPOINT_SIGNATURE_LOCATION).strip()
    if sig_loc:
        lower = sig_loc.lower()
        if lower.endswith((".png", ".jpg", ".jpeg")):
            ref_sig_bytes = download_sharepoint_file(
                location=sig_loc, web_url=req.web_url, fetch_mode=req.fetch_mode
            )
        else:
            entries = list_sharepoint_files(
                folder_location=sig_loc,
                web_url=req.web_url,
                typefile="all",
            )
            img_entries = [
                e
                for e in entries
                if str(e).strip().lower().endswith((".png", ".jpg", ".jpeg"))
            ]
            if img_entries:
                base_folder = sig_loc.rstrip("/")
                ref_sig_candidates = []
                for file_name in img_entries:
                    sig_file_loc = f"{base_folder}/{file_name}".replace("//", "/")
                    ref_bytes = download_sharepoint_file(
                        location=sig_file_loc, web_url=req.web_url, fetch_mode=req.fetch_mode
                    )
                    ref_sig_candidates.append((str(file_name), ref_bytes))

    name_a = req.location_a.split("/")[-1] or "sharepoint_file_a"
    name_b = req.location_b.split("/")[-1] or "sharepoint_file_b"

    return await _build_compare_response(
        content_a=content_a,
        content_b=content_b,
        name_a=name_a,
        name_b=name_b,
        ref_signature_bytes=ref_sig_bytes,
        ref_signature_candidates=ref_sig_candidates,
    )


@router.get(
    "/sharepoint/list-files",
    response_model=SharePointListFilesResponse,
    tags=["sharepoint"],
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
    tags=["sharepoint"],
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


@router.get(
    "/audit-history",
    response_model=CompareAuditHistoryResponse,
    tags=["audit"],
    summary="Lịch sử so sánh (phân trang)",
    description="Danh sách các lần so sánh đã ghi nhận (DB), sắp theo thời gian mới nhất.",
)
async def audit_history(
    limit: int = Query(20, ge=1, le=200, description="Số bản ghi tối đa mỗi request."),
    offset: int = Query(0, ge=0, description="Bỏ qua N bản ghi (offset phân trang)."),
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
    tags=["signatures"],
    summary="So sánh 2 ảnh chữ ký (PoC simple)",
    description="Hai ảnh base64; trả điểm tổng, quyết định và các thành phần overlap/shape/projection.",
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


@router.post(
    "/hand_signature_check",
    response_model=HandSignatureCheckResponse,
    tags=["signatures"],
    summary="Phát hiện chữ ký tay ở cuối trang và so sánh với chữ ký mẫu.",
    description=(
        "Không chạy full text diff. Chỉ render trang, tìm ROI chữ ký và so với file mẫu cố định trên server "
        "(localPDF/refSignatures/refSingnature.png). Tham số dpi/roi_mode/bottom_ratio/page_limit điều chỉnh độ chính xác/tốc độ."
    ),
)
async def hand_signature_check(
    file_a: UploadFile = File(..., description="File PDF gốc (A)."),
    file_b: UploadFile = File(..., description="File PDF chỉnh sửa (B)."),
    dpi: int = Query(180, ge=72, le=300),
    roi_mode: str = Query(
        "bottom_only",
        pattern="^(bottom_only|bottom_then_full)$",
        description="bottom_only: chỉ rà soát cuối trang; bottom_then_full: nếu không thấy, quét cả trang.",
    ),
    bottom_ratio: float = Query(
        0.35,
        ge=0.1,
        le=0.7,
        description="Tỷ lệ chiều cao đáy trang dùng làm ROI (vd 0.35 = 35% cuối trang).",
    ),
    page_limit: int | None = Query(
        None,
        ge=1,
        description="Nếu đặt, chỉ xử lý tối đa N trang từ đầu (tăng tốc cho file rất dài).",
    ),
) -> HandSignatureCheckResponse:
    """
    Render từng trang PDF A/B, ưu tiên rà soát vùng cuối trang để tìm chữ ký tay,
    sau đó so sánh với chữ ký mẫu `localPDF/refSignatures/refSingnature.png`.
    """
    content_a = await file_a.read()
    content_b = await file_b.read()

    ref_path = "localPDF/refSignatures/refSingnature.png"

    params = dict(
        dpi=dpi,
        roi_mode=roi_mode,
        bottom_ratio=bottom_ratio,
        page_limit=page_limit,
    )

    pages_a_raw = detect_and_compare_hand_signatures(
        pdf_bytes=content_a,
        ref_image_path=ref_path,
        **params,
    )
    pages_b_raw = detect_and_compare_hand_signatures(
        pdf_bytes=content_b,
        ref_image_path=ref_path,
        **params,
    )

    def _to_model_list(raw_list):
        out: list[HandSignaturePageResult] = []
        for item in raw_list:
            comps = item.get("components")
            components = (
                SignatureCompareComponents(
                    overlap_score=comps["overlap_score"],
                    shape_score=comps["shape_score"],
                    projection_score=comps["projection_score"],
                )
                if comps
                else None
            )
            out.append(
                HandSignaturePageResult(
                    page=item["page"],
                    has_signature=item["has_signature"],
                    best_score=item["best_score"],
                    decision=item.get("decision"),
                    bbox=tuple(item["bbox"]) if item.get("bbox") else None,
                    components=components,
                )
            )
        return out

    return HandSignatureCheckResponse(
        pages_a=_to_model_list(pages_a_raw),
        pages_b=_to_model_list(pages_b_raw),
    )
