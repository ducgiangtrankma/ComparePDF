from __future__ import annotations

import cv2
import numpy as np

from app.services.signature_compare_config import ALIGN_ANGLES_DEG, ALIGN_MAX_SHIFT_PX, to_binary_u8


def align_test_to_ref(ref: np.ndarray, test: np.ndarray) -> np.ndarray:
    """
    Căn ảnh test theo ref bằng:
    - xoay nhẹ quanh tâm (một vài góc cố định)
    - dịch (tx, ty) trong phạm vi +/- ALIGN_MAX_SHIFT_PX

    Tiêu chí: tối đa Dice trên mask nhị phân.
    Input ref/test là ảnh nhị phân uint8 {0,255} cùng kích thước.
    """
    h, w = ref.shape[:2]
    a_mask = ref > 0
    center = (w / 2.0, h / 2.0)

    best_tx, best_ty = 0, 0
    best_angle = 0.0
    best_dice = -1.0

    for angle in ALIGN_ANGLES_DEG:
        rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            test,
            rot_mat,
            (w, h),
            flags=cv2.INTER_NEAREST,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=0,
        )
        rotated = to_binary_u8(rotated)

        for ty in range(-ALIGN_MAX_SHIFT_PX, ALIGN_MAX_SHIFT_PX + 1):
            for tx in range(-ALIGN_MAX_SHIFT_PX, ALIGN_MAX_SHIFT_PX + 1):
                m = np.float32([[1, 0, tx], [0, 1, ty]])
                shifted = cv2.warpAffine(
                    rotated,
                    m,
                    (w, h),
                    flags=cv2.INTER_NEAREST,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=0,
                )
                shifted = to_binary_u8(shifted)

                b_mask = shifted > 0
                inter = int(np.logical_and(a_mask, b_mask).sum())
                denom = int(a_mask.sum() + b_mask.sum())
                if denom <= 0:
                    continue
                d = float(2.0 * inter / denom)
                if d > best_dice:
                    best_dice = d
                    best_tx, best_ty, best_angle = tx, ty, angle

    rot_mat = cv2.getRotationMatrix2D(center, best_angle, 1.0)
    rotated_best = cv2.warpAffine(
        test,
        rot_mat,
        (w, h),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    rotated_best = to_binary_u8(rotated_best)

    m = np.float32([[1, 0, best_tx], [0, 1, best_ty]])
    aligned = cv2.warpAffine(
        rotated_best,
        m,
        (w, h),
        flags=cv2.INTER_NEAREST,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=0,
    )
    return to_binary_u8(aligned)

