from __future__ import annotations

import numpy as np

# -----------------------------
# Tham số tinh chỉnh (PoC)
# -----------------------------
# Cân bằng độ chính xác vs độ nhạy (recall).
# Nếu cùng người ký mà điểm thấp: tăng trọng số shape/projection, giảm overlap.
# Nếu khác người mà điểm cao: siết ngưỡng decision hoặc tăng overlap.

# Kích thước canvas sau chuẩn hóa (giữ cố định để điểm ổn định).
NORM_WIDTH = 256
NORM_HEIGHT = 128

# Phạm vi tìm căn chỉnh (dịch), đơn vị pixel trên canvas đã chuẩn hóa.
ALIGN_MAX_SHIFT_PX = 36

# Góc xoay thử để bù lệch do scan/chụp (độ).
ALIGN_ANGLES_DEG = (0.0, -5.0, 5.0)

# Trọng số điểm tổng (nên cộng = 1.0).
# Theo spec tối ưu: overlap thấp, shape cao.
WEIGHT_OVERLAP = 0.10
WEIGHT_SHAPE = 0.55
WEIGHT_PROJECTION = 0.35

# Ngưỡng phân loại (0..100) – chỉ để tham khảo cho decision string.
THRESH_HIGH = 80.0  # Khớp cao
THRESH_MED = 65.0  # Khá giống


def to_binary_u8(img: np.ndarray, threshold: int = 127) -> np.ndarray:
    """Ép ảnh về mask nhị phân uint8 {0,255}."""
    return ((img > threshold).astype(np.uint8)) * 255

