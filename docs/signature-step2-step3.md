# Chữ ký PDF: ghi chú triển khai Step 2 & Step 3

Tài liệu này ghi lại **những gì cần chuẩn bị / cung cấp** khi phát triển tiếp (không mô tả code hiện tại). Step 1 trong codebase chỉ phát hiện field chữ ký qua AcroForm; Step 2 và 3 hiện là stub trong `app/services/pdf_signature.py`.

---

## Step 2 — Xác minh mật mã PKCS#7 / CMS (chữ ký “detached” trong PDF)

**Mục tiêu:** Kiểm tra tính toàn vẹn của vùng `ByteRange` + nội dung PKCS#7 (thường DER) trong dictionary chữ ký, và (tuỳ cấu hình) chuỗi chứng thư tới CA tin cậy.

### Không cần

- **Private key** của người ký (verify chỉ dùng chứng thư công khai kèm trong chữ ký hoặc trong SignedData).

### Thường cần cung cấp / cấu hình

| Hạng mục | Ghi chú |
|----------|---------|
| **Trust store (CA tin cậy)** | File PEM/DER các **root** (và có thể **intermediate**) mà tổ chức chấp nhận; hoặc dùng kho tin cậy OS / Mozilla / Java `cacerts` — tùy thư viện (ví dụ `cryptography`, OpenSSL bindings). |
| **Chính sách tin cậy nội bộ** | CA doanh nghiệp, chữ ký tự cấp: bắt buộc phải **nhập tay** root/intermediate vào trust. |
| **Mạng ra ngoài (tuỳ chọn nhưng nên có)** | **OCSP** / **CRL** để kiểm tra thu hồi chứng thư; URL thường nằm trong chứng thư hoặc metadata chữ ký. |
| **Tải chứng thư bổ sung** | Một số chữ ký thiếu intermediate: cần theo **AIA / Issuer URL** (HTTP) để hoàn thiện chuỗi. |
| **Chọn revision** | PDF ký nhiều lần (incremental updates): cần rõ **verify revision nào** (byte range theo từng lần ký). |

### Phụ thuộc kỹ thuật (gợi ý khi chọn stack)

- Thư viện parse CMS/PKCS#7 + verify chữ ký (`cryptography`, `asn1crypto`, hoặc tích hợp OpenSSL).
- Xử lý **lỗi** (PDF hỏng, nhiều chữ ký, encoding) và **timeout** khi gọi OCSP/HTTP.

---

## Step 3 — PAdES “nâng cao” (LTV, DSS, timestamp, v.v.)

**Mục tiêu:** Đi xa hơn một lần verify CMS: đối chiếu với **PAdES** (PDF Advanced Electronic Signatures) — thường gồm **DSS** (Document Security Store), chứng thư/thu hồi nhúng hoặc tham chiếu, **dấu thời gian (TSA)**, và (tuỳ bản PAdES) **LTV** để sau này vẫn verify được khi CA không còn phục vụ OCSP.

### Cần thêm so với Step 2

| Hạng mục | Ghi chú |
|----------|---------|
| **Tin cậy TSA** | Nếu có **timestamp token**: cần trust anchor cho **TSA** (và có thể policy “chỉ chấp nhận TSA X”). |
| **DSS / catalog extensions** | Đọc cấu trúc PDF (dictionary `DSS`, CRLs, OCSP responses nhúng) — thường cần parser PDF + hiểu ISO 32000 / ETSI TS 102 778 (PAdES). |
| **Chính sách LTV** | Quyết định: có bắt buộc **nhúng** OCSP/CRL vào DSS sau ký không, hay chỉ verify “tại thời điểm gọi API”. |
| **Thư viện chuyên sâu (gợi ý)** | **pyHanko** (Python) hoặc tương đương: hỗ trợ PAdES/LTV/DSS tốt hơn tự viết từ đầu. |
| **Hiệu năng & cache** | Nhiều file / nhiều chữ ký: cache chứng thư, giới hạn song song OCSP. |

### Vẫn không cần

- Private key người ký cho thao tác **verify** thuần túy.

---

## Gợi ý biến môi trường / cấu hình (khi implement)

Có thể bổ sung sau trong `.env` (chỉ là định hướng):

- Đường dẫn thư mục/file **CA bundle** tin cậy (PEM).
- Bật/tắt **OCSP** / **CRL** / **strict chain**.
- Timeout HTTP cho OCSP/AIA.
- (Step 3) Chính sách **TSA** / **LTV** (on/off).

---

## Liên kết code hiện tại

- Phát hiện field (Step 1): `app/services/pdf_signature.py` — `detect_digital_signatures`.
- Stub Step 2 / 3: cùng file — `verify_pkcs7_detached`, `verify_pades_advanced` (chưa gọi từ API).
