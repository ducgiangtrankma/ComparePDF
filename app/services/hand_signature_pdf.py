from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any, Literal

import cv2
import fitz  # PyMuPDF
import numpy as np

from app.services.signature_compare import compare_signatures_base64


RoiMode = Literal["bottom_only", "bottom_then_full"]


@dataclass
class HandSignaturePageResult:
    page: int
    has_signature: bool
    best_score: float
    decision: str | None
    bbox: tuple[int, int, int, int] | None
    components: dict[str, float] | None


def _render_page_gray(doc: fitz.Document, page_index: int, dpi: int) -> np.ndarray:
    page = doc.load_page(page_index)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    return gray


def _bottom_roi(bin_img: np.ndarray, bottom_ratio: float) -> tuple[np.ndarray, int]:
    h, _ = bin_img.shape[:2]
    cutoff = int(h * (1.0 - bottom_ratio))
    cutoff = max(0, min(h - 1, cutoff))
    roi = bin_img[cutoff:, :]
    return roi, cutoff


def _binarize(gray: np.ndarray) -> np.ndarray:
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    _th, bin_img = cv2.threshold(
        blur,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )
    kernel = np.ones((2, 2), dtype=np.uint8)
    bin_img = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, kernel, iterations=1)
    bin_img = cv2.morphologyEx(bin_img, cv2.MORPH_CLOSE, kernel, iterations=1)
    return bin_img


def _find_candidate_bboxes(
    bin_img: np.ndarray,
    min_area: int,
    max_area: int,
) -> list[tuple[int, int, int, int]]:
    contours, _ = cv2.findContours(bin_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = bin_img.shape[:2]
    results: list[tuple[int, int, int, int]] = []
    for cnt in contours:
        x, y, cw, ch = cv2.boundingRect(cnt)
        area = cw * ch
        if area < min_area or area > max_area:
            continue
        # Loại bỏ block gần sát mép trái/phải (thường là cột text)
        if x < 0.02 * w or x + cw > 0.98 * w:
            continue
        aspect = cw / float(ch + 1e-6)
        if aspect < 1.5:  # chữ ký thường khá ngang
            continue
        results.append((x, y, cw, ch))
    return results


def _pad_bbox(
    bbox: tuple[int, int, int, int],
    img_w: int,
    img_h: int,
    pad_ratio: float = 0.08,
) -> tuple[int, int, int, int]:
    x, y, w, h = bbox
    pad = int(max(w, h) * pad_ratio)
    x1 = max(0, x - pad)
    y1 = max(0, y - pad)
    x2 = min(img_w, x + w + pad)
    y2 = min(img_h, y + h + pad)
    return (x1, y1, max(1, x2 - x1), max(1, y2 - y1))


def _crop_to_base64(bin_img: np.ndarray, bbox: tuple[int, int, int, int]) -> str:
    x, y, w, h = bbox
    h_img, w_img = bin_img.shape[:2]
    x = max(0, min(w_img - 1, x))
    y = max(0, min(h_img - 1, y))
    w = max(1, min(w_img - x, w))
    h = max(1, min(h_img - y, h))
    crop = bin_img[y : y + h, x : x + w]

    # Re-crop theo foreground trong crop để giảm nền trắng dư.
    ys, xs = np.where(crop > 0)
    if len(xs) > 0 and len(ys) > 0:
        cx1, cx2 = int(xs.min()), int(xs.max()) + 1
        cy1, cy2 = int(ys.min()), int(ys.max()) + 1
        crop = crop[cy1:cy2, cx1:cx2]

    ok, buf = cv2.imencode(".png", crop)
    if not ok:
        raise ValueError("Không encode được ảnh crop chữ ký.")
    b64 = base64.b64encode(buf.tobytes()).decode("ascii")
    return b64


def _best_match_for_page(
    gray: np.ndarray,
    bin_img: np.ndarray,
    roi_mask_start_y: int,
    roi_bin: np.ndarray,
    ref_b64: str,
) -> HandSignaturePageResult:
    h, w = roi_bin.shape[:2]
    min_area = int(0.01 * w * h)
    max_area = int(0.35 * w * h)
    bboxes_roi = _find_candidate_bboxes(roi_bin, min_area=min_area, max_area=max_area)

    if not bboxes_roi:
        return HandSignaturePageResult(
            page=0,
            has_signature=False,
            best_score=0.0,
            decision=None,
            bbox=None,
            components=None,
        )

    best: HandSignaturePageResult | None = None
    for (x, y, cw, ch) in bboxes_roi:
        bbox_full = (x, y + roi_mask_start_y, cw, ch)
        # Pad nhẹ để tránh hụt nét ký ở biên bbox.
        bbox_full = _pad_bbox(bbox_full, img_w=gray.shape[1], img_h=gray.shape[0])
        # So sánh trên crop binary để giảm nhiễu anti-alias từ render PDF.
        cand_b64 = _crop_to_base64(bin_img, bbox_full)
        result = compare_signatures_base64(signature_ref=ref_b64, signature_test=cand_b64)
        score = float(result["final_score"])
        page_res = HandSignaturePageResult(
            page=0,
            # Việc quyết định đúng/sai để người dùng tự đánh giá; ở đây chỉ trả điểm.
            has_signature=False,
            best_score=score,
            decision=str(result["decision"]),
            bbox=bbox_full,
            components={k: float(v) for k, v in result["components"].items()},
        )
        if best is None or page_res.best_score > best.best_score:
            best = page_res

    assert best is not None
    return best


def detect_and_compare_hand_signatures(
    pdf_bytes: bytes,
    ref_image_path: str,
    *,
    dpi: int = 180,
    roi_mode: RoiMode = "bottom_only",
    bottom_ratio: float = 0.35,
    page_limit: int | None = None,
) -> list[dict[str, Any]]:
    """
    Render từng trang PDF, dò chữ ký tay ở cuối trang, so sánh với mẫu ref.
    Trả về list kết quả theo trang (1-based page index trong caller).
    """
    with open(ref_image_path, "rb") as f:
        ref_b64 = base64.b64encode(f.read()).decode("ascii")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        total_pages = doc.page_count
        if page_limit is not None:
            total_pages = min(total_pages, page_limit)

        results: list[dict[str, Any]] = []
        for idx in range(total_pages):
            gray = _render_page_gray(doc, idx, dpi=dpi)
            bin_img = _binarize(gray)

            # Bước 1: chỉ quét đáy trang
            roi_bin, offset_y = _bottom_roi(bin_img, bottom_ratio=bottom_ratio)
            best = _best_match_for_page(
                gray=gray,
                bin_img=bin_img,
                roi_mask_start_y=offset_y,
                roi_bin=roi_bin,
                ref_b64=ref_b64,
            )
            best.page = idx + 1

            # Nếu cho phép fallback toàn trang (ví dụ chữ ký không nằm hẳn dưới đáy)
            if roi_mode == "bottom_then_full":
                full_best = _best_match_for_page(
                    gray=gray,
                    bin_img=bin_img,
                    roi_mask_start_y=0,
                    roi_bin=bin_img,
                    ref_b64=ref_b64,
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
                }
            )
        return results
    finally:
        doc.close()

