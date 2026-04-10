# ComparePDF Tech Stack

## 1) Ngôn ngữ và nền tảng

- **Python 3.12**
- Môi trường chạy:
  - Local qua `uvicorn`
  - Container qua `Docker` + `docker-compose`

## 2) Backend API

- **FastAPI**
  - Xây dựng REST API cho:
    - So sánh nội dung PDF
    - Phát hiện chữ ký số
    - So sánh chữ ký tay (image-level + PDF-level)
    - Tích hợp SharePoint
- **Uvicorn**
  - ASGI server để chạy ứng dụng FastAPI
- **Pydantic v2**
  - Khai báo schema request/response
  - Validation dữ liệu đầu vào

## 3) Xử lý PDF

- **PyMuPDF (fitz)**
  - Đọc PDF
  - Trích xuất text theo trang
  - Render trang PDF thành ảnh cho detect chữ ký tay
- **pypdf**
  - Đọc AcroForm fields
  - Phát hiện sự hiện diện chữ ký số (digital signature fields)

## 4) So sánh nội dung văn bản

- Module nội bộ:
  - `app/services/pdf_reader.py`
  - `app/services/comparator.py`
  - `app/services/text_processor.py`
- Thuật toán chính:
  - So sánh text theo page
  - Tạo diff ở mức từ/cụm từ
  - Tổng hợp số lượng khác biệt

## 5) Xử lý ảnh và chữ ký tay

- **OpenCV (`opencv-python-headless`)**
  - Tiền xử lý ảnh chữ ký:
    - Gray, blur, threshold Otsu, morphology
  - Phát hiện contour/bbox vùng chữ ký
  - Căn chỉnh chữ ký (dịch + xoay nhẹ)
- **NumPy**
  - Ma trận ảnh
  - Tính toán vector/projection/similarity

### Thành phần so sánh chữ ký tay

- `overlap_score` (IoU trên binary mask)
- `shape_score` (shape matching)
- `projection_score` (cosine similarity theo profile hàng/cột)
- `final_score` theo weighted formula trong config

### Multi-reference

- Hỗ trợ nhiều mẫu chữ ký (best-of-references)
- Trả `matched_reference` cho mỗi trang để biết mẫu nào khớp nhất

## 6) Tích hợp SharePoint

- **requests**
  - Gọi Power Automate / SharePoint endpoints
- Hai mode fetch:
  - `power_automate` (qua Logic App URL)
  - `rest` (SharePoint REST + user/pass)
- Chức năng:
  - Download file PDF từ SharePoint
  - List file trong folder SharePoint
  - Lấy file chữ ký mẫu từ file path hoặc folder

## 7) AI summary (tuỳ chọn)

- **OpenAI SDK (`openai`)**
  - Tạo tóm tắt ngắn cho kết quả compare (nếu cấu hình API key)

## 8) Audit và dữ liệu

- **SQLAlchemy 2**
  - ORM cho bảng lưu lịch sử compare
- **PostgreSQL**
  - Lưu audit compare theo thời gian
- **psycopg (binary)**
  - Driver kết nối Postgres
- **File logging**
  - Ghi log compare ra file (`COMPARE_LOG_PATH`)

## 9) DevOps / Vận hành

- **Dockerfile**
  - Build image API production
- **docker-compose**
  - Orchestrate `api` + `postgres`
  - Port map API (`8000`) và DB (`5432`)
- Healthcheck:
  - API endpoint `/docs`
  - Postgres `pg_isready`

## 10) Cấu hình môi trường

- **python-dotenv**
  - Nạp biến môi trường từ `.env`
- Các nhóm biến chính:
  - OpenAI
  - SharePoint (web URL, fetch/list URL, auth)
  - Database (`DATABASE_URL`)
  - Logging/audit (`COMPARE_LOG_PATH`, `COMPARE_WRITE_DB`)

## 11) Testing / Smoke test

- Script: `test_local.py`
  - Khởi động server local
  - Gọi API compare
  - Lưu JSON output vào thư mục `output/`
  - Hỗ trợ smoke test nhánh chữ ký tay

## 12) Danh sách dependency chính

- `fastapi`
- `uvicorn`
- `PyMuPDF`
- `pypdf`
- `pydantic`
- `requests`
- `openai`
- `python-dotenv`
- `sqlalchemy`
- `psycopg[binary]`
- `numpy`
- `opencv-python-headless`

