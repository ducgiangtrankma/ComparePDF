# Handwritten Signature Comparison – Optimization Spec

## 1. Mục tiêu

Tối ưu hệ thống so sánh **2 chữ ký dạng ảnh scan** để:

* Tăng độ chính xác khi cùng một chữ ký đi qua pipeline (PDF → detect → compare)
* Giảm sensitivity với resize / render / anti-alias
* Đảm bảo score ổn định (>80) với cùng chữ ký

---

## 2. Vấn đề hiện tại

### Hiện tượng

* Cùng một chữ ký
* Đưa vào PDF → detect lại
* So với ảnh gốc → score < 50

### Kết luận

Pipeline hiện tại đang:

* So pixel raster thay vì shape thực
* Nhạy với anti-alias / resize
* Bị lệch do crop / align

---

## 3. Root Cause (Nguyên nhân chính)

### 3.1 Resize sai interpolation

* Dùng `INTER_AREA` trên ảnh nhị phân
* Sinh ra pixel xám → làm sai mask

### 3.2 Không re-binarize sau transform

* Sau resize / warp ảnh không còn binary
* Projection & overlap bị nhiễu

### 3.3 Overlap score quá nặng

* Phụ thuộc pixel match 1-1
* Không chịu được sai lệch nhỏ

### 3.4 Crop / bbox không ổn định

* Bounding box thiếu nét hoặc dư padding

### 3.5 Projection dùng intensity thay vì mask

* Bị ảnh hưởng bởi mức xám

---

## 4. Giải pháp tối ưu

## 4.1 Chuẩn hoá pipeline (BẮT BUỘC)

### Preprocessing thống nhất

* Grayscale
* Gaussian blur nhẹ (optional)
* Otsu threshold (cùng 1 method cho tất cả ảnh)

### Sau mọi transform (resize/warp)

BẮT BUỘC:

```python
img = (img > 127).astype(np.uint8) * 255
```

---

## 4.2 Resize đúng cách

❌ Sai:

```python
cv2.resize(..., INTER_AREA)
```

✅ Đúng:

```python
cv2.resize(..., INTER_NEAREST)
```

### Giữ tỷ lệ

* Resize theo cạnh dài
* Pad vào canvas
* Không kéo giãn

---

## 4.3 Crop chuẩn

* Crop theo bounding box của foreground
* Thêm padding nhẹ (5–10%)

---

## 4.4 Alignment

* Center alignment
* Optional: thử shift ± vài pixel để maximize overlap

---

## 4.5 Feature cải tiến

### 1. Overlap (giảm trọng số)

* IoU trên mask nhị phân

### 2. Shape (tăng trọng số)

* Dùng contour lớn nhất
* `cv2.matchShapes`

### 3. Projection (sửa lại)

❌ Sai:

```python
sum(pixel intensity)
```

✅ Đúng:

```python
sum(binary mask)
```

---

## 4.6 Công thức mới

```text
final_score =
  0.1 * overlap_score +
  0.55 * shape_score +
  0.35 * projection_score
```

---

## 5. Fix cụ thể trong code

### 5.1 Normalize canvas

```python
resized = cv2.resize(img, size, interpolation=cv2.INTER_NEAREST)
```

### 5.2 Sau align

```python
aligned = cv2.warpAffine(...)
aligned = ((aligned > 127).astype(np.uint8)) * 255
```

### 5.3 Projection

```python
mask = (img > 127).astype(float)
```

### 5.4 Shape (đề xuất)

```python
cv2.matchShapes(contour1, contour2, ...)
```

---

## 6. Test Plan (QUAN TRỌNG)

### Case 1

* Image vs chính nó
  → Expect: >95

### Case 2

* Image vs resized image
  → Expect: >85

### Case 3

* Image vs PDF render (no detect)
  → Expect: >80

### Case 4

* Image vs PDF detect
  → So sánh với Case 3 để xác định lỗi detect

---

## 7. KPI sau tối ưu

| Case       | Target |
| ---------- | ------ |
| Same image | >95    |
| Resize     | >85    |
| PDF render | >80    |
| PDF detect | >75    |

---

## 8. Debug cần có

BẮT BUỘC lưu:

* binary ref
* binary test
* overlay before align
* overlay after align

---

## 9. Tech stack

* Python
* OpenCV
* NumPy
* (Optional) scikit-image

---

## 10. Roadmap

### Phase 1

* Fix pipeline CV
* Stabilize score

### Phase 2

* Multi-sample reference

### Phase 3

* Siamese / embedding model

---

## 11. Kết luận

Vấn đề hiện tại KHÔNG phải do thuật toán yếu, mà do:

* preprocessing không chuẩn
* resize sai
* scoring sai trọng tâm

Sau khi fix pipeline:
→ cùng chữ ký qua PDF phải đạt >80 score

Nếu chưa đạt → lỗi nằm ở detect bbox, không phải compare
