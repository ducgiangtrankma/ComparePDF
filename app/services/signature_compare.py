from __future__ import annotations

import base64
from typing import Any

import cv2
import numpy as np

from app.services.signature_compare_align import align_test_to_ref
from app.services.signature_compare_config import (
    NORM_HEIGHT,
    NORM_WIDTH,
    THRESH_HIGH,
    THRESH_MED,
    WEIGHT_OVERLAP,
    WEIGHT_PROJECTION,
    WEIGHT_SHAPE,
    to_binary_u8,
)
from app.services.signature_compare_features import (
    overlap_iou_score,
    projection_score,
    shape_match_score,
)


def _decode_base64_image_to_gray(data: str) -> np.ndarray:
    raw = data.strip()
    if "," in raw and raw.split(",", 1)[0].startswith("data:"):
        raw = raw.split(",", 1)[1]
    try:
        image_bytes = base64.b64decode(raw, validate=True)
    except Exception as exc:
        raise ValueError("Invalid base64 image data.") from exc

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError("Cannot decode signature image.")
    return img


def _preprocess_signature(gray: np.ndarray) -> np.ndarray:
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    # Nhị phân nghịch: vùng mực (foreground) = 255
    _th, bin_img = cv2.threshold(
        blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
    )
    kernel = np.ones((2, 2), dtype=np.uint8)
    bin_img = cv2.morphologyEx(bin_img, cv2.MORPH_OPEN, kernel, iterations=1)
    bin_img = cv2.morphologyEx(bin_img, cv2.MORPH_CLOSE, kernel, iterations=1)
    return bin_img


def _crop_foreground(bin_img: np.ndarray) -> np.ndarray:
    ys, xs = np.where(bin_img > 0)
    if len(xs) == 0 or len(ys) == 0:
        raise ValueError("Signature image has no foreground content.")
    x1, x2 = int(xs.min()), int(xs.max()) + 1
    y1, y2 = int(ys.min()), int(ys.max()) + 1

    # Padding nhẹ để bbox ổn định hơn (5% theo cạnh dài).
    h, w = bin_img.shape[:2]
    pad = int(max(x2 - x1, y2 - y1) * 0.05)
    x1 = max(0, x1 - pad)
    y1 = max(0, y1 - pad)
    x2 = min(w, x2 + pad)
    y2 = min(h, y2 + pad)
    return bin_img[y1:y2, x1:x2]


def _normalize_canvas(
    bin_img: np.ndarray, width: int = NORM_WIDTH, height: int = NORM_HEIGHT
) -> np.ndarray:
    h, w = bin_img.shape[:2]
    if h <= 0 or w <= 0:
        raise ValueError("Invalid signature dimensions.")

    scale = min(width / w, height / h)
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))

    # Ảnh nhị phân phải resize bằng INTER_NEAREST để tránh sinh pixel xám.
    resized = cv2.resize(bin_img, (nw, nh), interpolation=cv2.INTER_NEAREST)
    resized = to_binary_u8(resized)
    canvas = np.zeros((height, width), dtype=np.uint8)

    x = (width - nw) // 2
    y = (height - nh) // 2
    canvas[y : y + nh, x : x + nw] = resized
    return canvas


def _decision(final_score: float) -> str:
    if final_score >= THRESH_HIGH:
        return "Khớp cao"
    if final_score >= THRESH_MED:
        return "Khá giống"
    return "Khác"


def compare_signatures_base64(signature_ref: str, signature_test: str) -> dict[str, Any]:
    """
    Bước 1 PoC: so sánh 2 ảnh chữ ký (chuỗi base64).
    Luồng: giải mã -> tiền xử lý -> crop -> chuẩn hóa canvas -> căn test theo ref (tịnh tiến)
    -> điểm overlap / shape / projection -> điểm tổng có trọng số + nhãn kết luận.
    """
    ref_gray = _decode_base64_image_to_gray(signature_ref)
    test_gray = _decode_base64_image_to_gray(signature_test)

    ref_bin = _preprocess_signature(ref_gray)
    test_bin = _preprocess_signature(test_gray)

    ref_crop = _crop_foreground(ref_bin)
    test_crop = _crop_foreground(test_bin)

    ref_norm = _normalize_canvas(ref_crop)
    test_norm = _normalize_canvas(test_crop)

    test_aligned = align_test_to_ref(ref_norm, test_norm)
    overlap = overlap_iou_score(ref_norm, test_aligned)
    shape = shape_match_score(ref_norm, test_aligned)
    projection = projection_score(ref_norm, test_aligned)

    # Overlap dễ trừ điểm khi hai mẫu thật cùng người; shape/projection mang tín hiệu nhiều hơn.
    final_score = (
        WEIGHT_OVERLAP * overlap
        + WEIGHT_SHAPE * shape
        + WEIGHT_PROJECTION * projection
    )
    final_score = max(0.0, min(100.0, float(final_score)))

    return {
        "final_score": round(final_score, 1),
        "decision": _decision(final_score),
        "components": {
            "overlap_score": round(float(overlap), 1),
            "shape_score": round(float(shape), 1),
            "projection_score": round(float(projection), 1),
        },
    }

