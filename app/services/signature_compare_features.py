from __future__ import annotations

import math

import cv2
import numpy as np

from app.services.signature_compare_config import to_binary_u8


def overlap_iou_score(a: np.ndarray, b: np.ndarray) -> float:
    """IoU trên mask nhị phân (0..100)."""
    a_mask = a > 0
    b_mask = b > 0
    inter = int(np.logical_and(a_mask, b_mask).sum())
    union = int(np.logical_or(a_mask, b_mask).sum())
    if union <= 0:
        return 0.0
    return float(inter / union * 100.0)


def _largest_contour(mask_u8: np.ndarray) -> np.ndarray | None:
    cnts, _ = cv2.findContours(mask_u8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None
    return max(cnts, key=cv2.contourArea)


def shape_match_score(a: np.ndarray, b: np.ndarray) -> float:
    """
    Shape score (0..100) dựa trên `cv2.matchShapes` của contour lớn nhất.
    matchShapes trả về khoảng cách (càng nhỏ càng giống) → map sang điểm.
    """
    a_u8 = to_binary_u8(a)
    b_u8 = to_binary_u8(b)
    c1 = _largest_contour(a_u8)
    c2 = _largest_contour(b_u8)
    if c1 is None or c2 is None:
        return 0.0

    dist = float(cv2.matchShapes(c1, c2, cv2.CONTOURS_MATCH_I1, 0.0))
    # Map dist -> score. dist thường nhỏ (<2) nếu khá giống.
    score = math.exp(-dist * 2.0) * 100.0
    return max(0.0, min(100.0, score))


def projection_score(a: np.ndarray, b: np.ndarray) -> float:
    """
    Projection score (0..100) dựa trên mask nhị phân, không dùng intensity xám.
    So sánh cosine similarity của profile theo hàng và cột.
    """
    a_mask = (to_binary_u8(a) > 0).astype(np.float64)
    b_mask = (to_binary_u8(b) > 0).astype(np.float64)

    a_row = a_mask.sum(axis=1)
    b_row = b_mask.sum(axis=1)
    a_col = a_mask.sum(axis=0)
    b_col = b_mask.sum(axis=0)

    def _cos_sim(x: np.ndarray, y: np.ndarray) -> float:
        nx = float(np.linalg.norm(x))
        ny = float(np.linalg.norm(y))
        if nx == 0.0 or ny == 0.0:
            return 0.0
        val = float(np.dot(x, y) / (nx * ny))
        return max(-1.0, min(1.0, val))

    row_sim = _cos_sim(a_row, b_row)
    col_sim = _cos_sim(a_col, b_col)
    return float(((row_sim + col_sim) / 2.0) * 100.0)

