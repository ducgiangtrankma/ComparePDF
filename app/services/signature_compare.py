from __future__ import annotations

import base64
import math
from typing import Any

import cv2
import numpy as np


# -----------------------------
# Tham số tinh chỉnh (PoC)
# -----------------------------
# Cân bằng độ chính xác vs độ nhạy (recall).
# Cùng người ký mà điểm thấp: nới ngưỡng / giảm trọng số overlap.
# Khác người mà điểm cao: siết ngưỡng / tăng trọng số overlap.

# Kích thước canvas sau chuẩn hóa (giữ cố định để điểm ổn định).
NORM_WIDTH = 256
NORM_HEIGHT = 128

# Phạm vi tìm căn chỉnh (chỉ tịnh tiến), đơn vị pixel trên canvas đã chuẩn hóa.
# Tăng nếu crop lệch nhiều; giảm thì nhanh hơn và ít “khớp nhầm”.
ALIGN_MAX_SHIFT_PX = 36

# Điểm overlap: trộn IoU (chặt) và Dice (mềm hơn).
OVERLAP_BLEND_IOU = 0.35
OVERLAP_BLEND_DICE = 0.65

# Khoảng cách Hu moments -> độ mềm điểm (càng lớn càng dễ cho điểm).
HU_DECAY_DIVISOR = 6.0

# Trọng số điểm tổng (nên cộng = 1.0).
WEIGHT_OVERLAP = 0.15
WEIGHT_SHAPE = 0.45
WEIGHT_PROJECTION = 0.40

# Ngưỡng phân loại (0..100).
THRESH_HIGH = 75.0  # Khớp cao
THRESH_MED = 50.0  # Khá giống


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

    resized = cv2.resize(bin_img, (nw, nh), interpolation=cv2.INTER_AREA)
    canvas = np.zeros((height, width), dtype=np.uint8)

    x = (width - nw) // 2
    y = (height - nh) // 2
    canvas[y : y + nh, x : x + nw] = resized
    return canvas


def _align_test_to_ref(
    ref: np.ndarray, test: np.ndarray, max_shift: int = ALIGN_MAX_SHIFT_PX
) -> np.ndarray:
    """Dịch ảnh test trên canvas để tối đa chồng lấp với ref (cùng kích thước, mặt nạ nhị phân)."""
    h, w = ref.shape[:2]
    a_mask = ref > 0
    best_tx, best_ty = 0, 0
    best_dice = -1.0
    for ty in range(-max_shift, max_shift + 1):
        for tx in range(-max_shift, max_shift + 1):
            m = np.float32([[1, 0, tx], [0, 1, ty]])
            shifted = cv2.warpAffine(
                test,
                m,
                (w, h),
                flags=cv2.INTER_NEAREST,
                borderMode=cv2.BORDER_CONSTANT,
                borderValue=0,
            )
            b_mask = shifted > 0
            inter = int(np.logical_and(a_mask, b_mask).sum())
            denom = int(a_mask.sum() + b_mask.sum())
            if denom <= 0:
                continue
            d = float(2.0 * inter / denom)
            if d > best_dice:
                best_dice = d
                best_tx, best_ty = tx, ty
    m = np.float32([[1, 0, best_tx], [0, 1, best_ty]])
    return cv2.warpAffine(
        test,
        m,
        (w, h),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )


def _overlap_score(a: np.ndarray, b: np.ndarray) -> float:
    """Trộn IoU + Dice: Dice ít “gắt” hơn khi nét không khớp pixel-perfect."""
    a_mask = a > 0
    b_mask = b > 0
    inter = int(np.logical_and(a_mask, b_mask).sum())
    union = int(np.logical_or(a_mask, b_mask).sum())
    a_cnt = int(a_mask.sum())
    b_cnt = int(b_mask.sum())
    if union == 0:
        return 0.0
    iou = float(inter / union * 100.0)
    denom = a_cnt + b_cnt
    dice = float(2.0 * inter / denom * 100.0) if denom > 0 else 0.0
    # Ưu tiên Dice để hai lần ký cùng người không bị đè điểm quá mạnh.
    return float(OVERLAP_BLEND_IOU * iou + OVERLAP_BLEND_DICE * dice)


def _shape_score_hu(a: np.ndarray, b: np.ndarray) -> float:
    m1 = cv2.moments(a)
    m2 = cv2.moments(b)
    hu1 = cv2.HuMoments(m1).flatten()
    hu2 = cv2.HuMoments(m2).flatten()

    # Log để ổn định số học
    hu1 = np.array(
        [-math.copysign(1.0, x) * math.log10(abs(float(x)) + 1e-12) for x in hu1]
    )
    hu2 = np.array(
        [-math.copysign(1.0, x) * math.log10(abs(float(x)) + 1e-12) for x in hu2]
    )

    dist = float(np.mean(np.abs(hu1 - hu2)))
    # Hàm suy giảm mềm hơn => điểm cao hơn khi cùng người nhưng nét đổi nhẹ.
    score = math.exp(-dist / HU_DECAY_DIVISOR) * 100.0
    return max(0.0, min(100.0, score))


def _projection_score(a: np.ndarray, b: np.ndarray) -> float:
    a_row = a.sum(axis=1).astype(np.float64)
    b_row = b.sum(axis=1).astype(np.float64)
    a_col = a.sum(axis=0).astype(np.float64)
    b_col = b.sum(axis=0).astype(np.float64)

    def _cos_sim(x: np.ndarray, y: np.ndarray) -> float:
        nx = float(np.linalg.norm(x))
        ny = float(np.linalg.norm(y))
        if nx == 0.0 or ny == 0.0:
            return 0.0
        val = float(np.dot(x, y) / (nx * ny))
        return max(-1.0, min(1.0, val))

    row_sim = _cos_sim(a_row, b_row)
    col_sim = _cos_sim(a_col, b_col)
    score = ((row_sim + col_sim) / 2.0) * 100.0
    return max(0.0, min(100.0, score))


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

    test_aligned = _align_test_to_ref(ref_norm, test_norm)
    overlap = _overlap_score(ref_norm, test_aligned)
    shape = _shape_score_hu(ref_norm, test_aligned)
    projection = _projection_score(ref_norm, test_aligned)

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

