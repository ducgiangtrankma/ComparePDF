from __future__ import annotations

import base64
from typing import Any

import fitz  # PyMuPDF

from app.services.hand_signature_pdf import (
    _best_match_for_page,
    _binarize,
    _bottom_roi,
    _render_page_gray,
)


def detect_and_compare_hand_signatures(
    pdf_bytes: bytes,
    ref_image_path: str,
    *,
    dpi: int = 180,
    roi_mode: str = "bottom_only",
    bottom_ratio: float = 0.35,
    page_limit: int | None = None,
) -> list[dict[str, Any]]:
    with open(ref_image_path, "rb") as f:
        ref_bytes = f.read()
    return detect_and_compare_hand_signatures_with_ref_bytes(
        pdf_bytes=pdf_bytes,
        ref_image_bytes=ref_bytes,
        dpi=dpi,
        roi_mode=roi_mode,
        bottom_ratio=bottom_ratio,
        page_limit=page_limit,
    )


def detect_and_compare_hand_signatures_with_ref_bytes(
    pdf_bytes: bytes,
    ref_image_bytes: bytes,
    *,
    dpi: int = 180,
    roi_mode: str = "bottom_only",
    bottom_ratio: float = 0.35,
    page_limit: int | None = None,
) -> list[dict[str, Any]]:
    return detect_and_compare_hand_signatures_with_ref_candidates(
        pdf_bytes=pdf_bytes,
        ref_candidates=[("default_ref", ref_image_bytes)],
        dpi=dpi,
        roi_mode=roi_mode,
        bottom_ratio=bottom_ratio,
        page_limit=page_limit,
    )


def detect_and_compare_hand_signatures_with_ref_candidates(
    pdf_bytes: bytes,
    ref_candidates: list[tuple[str, bytes]],
    *,
    dpi: int = 180,
    roi_mode: str = "bottom_only",
    bottom_ratio: float = 0.35,
    page_limit: int | None = None,
) -> list[dict[str, Any]]:
    ref_b64_candidates = [(name, base64.b64encode(data).decode("ascii")) for name, data in ref_candidates]
    if not ref_b64_candidates:
        raise ValueError("Danh sách chữ ký mẫu trống.")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        total_pages = min(doc.page_count, page_limit) if page_limit is not None else doc.page_count
        results: list[dict[str, Any]] = []
        for idx in range(total_pages):
            gray = _render_page_gray(doc, idx, dpi=dpi)
            bin_img = _binarize(gray)
            roi_bin, offset_y = _bottom_roi(bin_img, bottom_ratio=bottom_ratio)
            best = _best_match_for_page(
                gray=gray,
                bin_img=bin_img,
                roi_mask_start_y=offset_y,
                roi_bin=roi_bin,
                ref_candidates=ref_b64_candidates,
            )
            best.page = idx + 1
            if roi_mode == "bottom_then_full":
                full_best = _best_match_for_page(
                    gray=gray,
                    bin_img=bin_img,
                    roi_mask_start_y=0,
                    roi_bin=bin_img,
                    ref_candidates=ref_b64_candidates,
                )
                full_best.page = idx + 1
                if full_best.best_score > best.best_score:
                    best = full_best
            results.append(
                {
                    "page": best.page,
                    "has_signature": best.has_signature,
                    "best_score": round(best.best_score, 1),
                    "decision": best.decision,
                    "bbox": best.bbox,
                    "components": best.components,
                    "matched_reference": best.matched_reference,
                }
            )
        return results
    finally:
        doc.close()

