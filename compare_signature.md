# Handwritten Signature Comparison (PoC)

## 1. Mục tiêu

Xây dựng module so sánh **2 chữ ký dạng ảnh scan** (không nhiễu, không bị đè dấu) để:

* Tính toán độ tương đồng (similarity score)
* Phân loại mức độ khớp
* Cung cấp dữ liệu debug trực quan

---

## 2. Input / Output

### Input

* `signature_ref`: ảnh chữ ký mẫu (PNG/JPG)
* `signature_test`: ảnh chữ ký cần kiểm tra

### Output

```json
{
  "final_score": 87.4,
  "decision": "Khớp cao",
  "components": {
    "overlap_score": 90.1,
    "shape_score": 84.2,
    "projection_score": 85.0
  }
}
```

---

## 3. Phạm vi (Scope)

### Included

* 2 ảnh chữ ký sạch
* Không có dấu, không bị chồng lấn
* Không cần detect vùng chữ ký

### Excluded (giai đoạn sau)

* PDF extraction
* Signature detection
* AI model (Siamese)
* Multi-signature matching

---

## 4. Kiến trúc tổng thể

```
Input Images
   ↓
Preprocessing
   ↓
Normalization
   ↓
Feature Extraction
   ↓
Similarity Calculation
   ↓
Final Score + Decision
```

---

## 5. Pipeline chi tiết

### 5.1 Preprocessing

* Convert grayscale
* Threshold (Otsu / Adaptive)
* Morphology (opening/closing nhẹ)

### 5.2 Crop chữ ký

* Detect bounding box của vùng foreground
* Crop sát nội dung

### 5.3 Normalize

* Resize về cùng kích thước (vd: 256x128)
* Center align
* Padding nếu cần

### 5.4 Alignment

* Center of mass alignment
* Optional: scale normalization

---

## 6. Feature & Similarity

### 6.1 Pixel Overlap Score

```
intersection / union
```

### 6.2 Shape Score

* Hu Moments
* Contour-based features

### 6.3 Projection Score

* Sum pixel theo hàng
* Sum pixel theo cột

---

## 7. Công thức tính điểm

```
final_score =
  0.5 * overlap_score +
  0.3 * shape_score +
  0.2 * projection_score
```

---

## 8. Decision Logic

| Score   | Kết luận  |
| ------- | --------- |
| >= 85   | Khớp cao  |
| 70 - 84 | Khá giống |
| < 70    | Khác      |

---

## 9. Debug Output (khuyến nghị)

* Overlay 2 chữ ký
* Highlight vùng trùng nhau
* Bounding box

---

## 10. Tech Stack

### Core

* Python
* OpenCV
* NumPy

### Optional

* scikit-image (skeletonization)
* matplotlib (debug visualization)

### API

* FastAPI

---

## 11. API Design

### POST /signature_compare

#### Request

```json
{
  "signature_ref": "base64",
  "signature_test": "base64"
}
```

#### Response

```json
{
  "final_score": 87.4,
  "decision": "Khop cao"
}
```

---
