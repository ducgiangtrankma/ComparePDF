# PDF Compare API

REST API so sánh nội dung text hiển thị giữa 2 file PDF.

## Cài đặt

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (CMD):**

```cmd
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

> Nếu PowerShell báo lỗi execution policy, chạy trước: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## Chạy server

**macOS / Linux:**

```bash
source .venv/bin/activate
uvicorn app.main:app --reload
```

**Windows:**

```cmd
.venv\Scripts\activate
uvicorn app.main:app --reload
```

Server chạy tại `http://127.0.0.1:8000`. Truy cập `http://127.0.0.1:8000/docs` để xem Swagger UI.

### Tóm tắt bằng AI (OpenAI, tùy chọn)

Nếu đặt biến môi trường `OPENAI_API_KEY`, mỗi response của `POST /compare-pdf` sẽ thêm trường `ai_summary` — đoạn văn tiếng Việt ngắn, dễ hiểu, tóm lược các khác biệt. Không có key thì `ai_summary` là `null`, phần so sánh vẫn chạy bình thường.

Cách đơn giản: copy `.env.example` thành file `.env` ở thư mục gốc project, điền `OPENAI_API_KEY=...` (file `.env` đã được gitignore).

```bash
export OPENAI_API_KEY="sk-..."
# Tuỳ chọn: mô hình (mặc định gpt-4o-mini)
export OPENAI_MODEL="gpt-4o-mini"
uvicorn app.main:app --reload
```

**Windows (CMD):** `set OPENAI_API_KEY=sk-...` rồi chạy uvicorn.

**Windows (PowerShell):** `$env:OPENAI_API_KEY="sk-..."`

## Sử dụng

### POST /compare-pdf

Upload 2 file PDF qua `multipart/form-data`:

```bash
curl -X POST http://127.0.0.1:8000/compare-pdf \
  -F "file_a=@document_v1.pdf" \
  -F "file_b=@document_v2.pdf"
```

### Response mẫu

**Khi 2 file giống nhau:**

```json
{
  "same": true,
  "summary": {
    "total_pages_a": 3,
    "total_pages_b": 3,
    "different_pages": 0
  },
  "differences": []
}
```

**Khi 2 file khác nhau:**

```json
{
  "same": false,
  "summary": {
    "total_pages_a": 3,
    "total_pages_b": 4,
    "different_pages": 2
  },
  "differences": [
    {
      "page": 2,
      "added": ["Dòng mới được thêm trong file B"],
      "removed": ["Dòng gốc từ file A"]
    },
    {
      "page": 4,
      "added": ["Nội dung trang dư trong file B"],
      "removed": []
    }
  ]
}
```

## Test local

Test nhanh không cần curl hay Swagger — script tự khởi động server, gọi API, lưu kết quả rồi tắt server.

**So sánh 2 file bất kỳ:**

macOS / Linux:

```bash
source .venv/bin/activate
python test_local.py localPDF/pdf1.pdf localPDF/pdf2.pdf
```

Windows:

```cmd
.venv\Scripts\activate
python test_local.py localPDF\pdf1.pdf localPDF\pdf2.pdf
```

Kết quả lưu tại `output/pdf1_vs_pdf2_result.json`.

**Auto-discover nhiều cặp (quy ước `*_a.pdf` / `*_b.pdf`):**

macOS / Linux:

```bash
source .venv/bin/activate
python generate_test_pdfs.py   # tạo PDF mẫu (tuỳ chọn)
python test_local.py           # chạy không tham số → tìm tất cả cặp _a/_b
```

Windows:

```cmd
.venv\Scripts\activate
python generate_test_pdfs.py
python test_local.py
```

## Cấu trúc project

```
├── generate_test_pdfs.py        # Tạo PDF mẫu vào localPDF/
├── test_local.py                # Chạy test local, kết quả vào output/
├── localPDF/                    # Chứa các cặp PDF cần so sánh
├── output/                      # Kết quả JSON sau khi compare
└── app/
    ├── __init__.py
    ├── main.py                  # FastAPI app entry point
    ├── router.py                # API endpoint definitions
    ├── schemas.py               # Pydantic request/response models
    ├── exceptions.py            # Custom PDF error classes
    └── services/
        ├── __init__.py
        ├── pdf_reader.py        # Extract text from PDF pages
        ├── text_processor.py    # Normalize text before comparing
        └── comparator.py        # Page-by-page diff logic
```

## Tech stack

- **FastAPI** - REST API framework
- **PyMuPDF** - PDF text extraction
- **Uvicorn** - ASGI server
- **Pydantic** - Data validation & serialization
- **difflib** - Text comparison (stdlib)
