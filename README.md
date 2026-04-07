# PDF Compare API

REST API so sánh **text hiển thị** giữa hai file PDF (diff theo từ + tổng hợp), tùy chọn **tóm tắt AI**, phát hiện **có field chữ ký số** (AcroForm, không verify mật mã), **audit** file log + PostgreSQL, và tích hợp **SharePoint** (Power Automate hoặc REST).

### Tính năng chính

| Khu vực | Mô tả |
|--------|--------|
| So sánh | `POST /compare-pdf` (upload), `POST /compare-pdf-sharepoint` (tải 2 file từ SharePoint) |
| Chữ ký (bước 1) | Mỗi response có `source_signature` / `target_signature` (`has_digital_signature`, `signature_count`, `field_names`) |
| SharePoint | `GET` và `POST /sharepoint/list-files`; ràng buộc folder (1–2 PDF) có thể tắt bằng `strict_folder_rules=false` |
| Audit | Log file + bảng `compare_audit`; `GET /audit-history` |
| Test local | `test_local.py` tự chạy uvicorn, **không ghi DB** (`COMPAREPDF_SKIP_DB_AUDIT=1`) |

### Endpoint nhanh

| Phương thức | Đường dẫn | Ghi chú |
|-------------|-----------|---------|
| `POST` | `/compare-pdf` | Upload 2 PDF (`multipart`) |
| `POST` | `/compare-pdf-sharepoint` | JSON: `location_a`, `location_b` (phải `.pdf`), `web_url`, `fetch_mode` |
| `GET` | `/sharepoint/list-files` | Query: `folder_location`, `web_url`, `typefile`, `strict_folder_rules` |
| `POST` | `/sharepoint/list-files` | JSON body cùng tham số |
| `GET` | `/audit-history` | Query: `limit`, `offset` |
| `GET` | `/docs` | Swagger UI |

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

### Deploy bằng Docker (API + PostgreSQL)

Cần **Docker** và **Docker Compose** (plugin `docker compose`). File `docker-compose.yml` build image từ `Dockerfile`, chạy service `api` (Uvicorn) và `postgres:16`, mạng nội bộ `comparepdf_net`.

1. Tạo `.env` từ `.env.example` và điền **OpenAI**, **SharePoint**, v.v. Biến `DATABASE_URL` trong `.env` (thường trỏ `localhost`) **bị ghi đè** trong Compose bằng chuỗi nối tới host `postgres` — không cần sửa tay khi chạy full stack.

2. Build và chạy nền:

```bash
docker compose up -d --build
```

3. API: `http://<máy-chủ>:8000` (đổi cổng: biến `API_PORT` trước khi chạy, mặc định `8000`). Swagger: `/docs`.

4. Xem log API: `docker compose logs -f api`

5. Dừng / gỡ: `docker compose down` (volume `postgres_data` giữ dữ liệu DB; thêm `-v` nếu muốn xoá volume).

**Chỉ PostgreSQL** (dev, không build API): vẫn dùng `docker compose -f docker-compose.postgres.yml up -d`.

**Database bên ngoài** (RDS, managed Postgres): chỉnh `docker-compose.yml` — xóa service `postgres`, bỏ `depends_on` / `environment.DATABASE_URL` cố định ở `api`, thêm `DATABASE_URL` trỏ tới host thật (hoặc dùng `env_file` + URL đúng). Đặt reverse proxy (Nginx, Traefik) và TLS phía trước API khi public internet.

### Cấu hình `.env`

Copy `.env.example` thành `.env` ở thư mục gốc (file này không commit). Các nhóm biến thường dùng:

| Nhóm | Biến (tham khảo) |
|------|-------------------|
| OpenAI (tuỳ chọn) | `OPENAI_API_KEY`, `OPENAI_MODEL` |
| SharePoint | `SHAREPOINT_WEB_URL`, `SHAREPOINT_FETCH_MODE` (`power_automate` \| `rest`), `SHAREPOINT_FETCH_URL`, `SHAREPOINT_LIST_URL`; REST thêm `SHAREPOINT_USERNAME`, `SHAREPOINT_PASSWORD` |
| Audit | `DATABASE_URL`, `COMPARE_LOG_PATH`, `COMPARE_WRITE_DB` |

## Ghi log và database

Trước khi trả response cho client, hệ thống sẽ:
- ghi log compare vào file (`COMPARE_LOG_PATH`, mặc định `logs/compare_audit.log`)
- ghi kết quả đầy đủ (JSON) vào PostgreSQL nếu có `DATABASE_URL` và ghi DB được bật

**Biến môi trường liên quan** (xem thêm `.env.example`):

| Biến | Ý nghĩa |
|------|---------|
| `DATABASE_URL` | Chuỗi kết nối SQLAlchemy + psycopg (PostgreSQL). Không có → không dùng DB. |
| `COMPARE_LOG_PATH` | Đường dẫn file log audit (mặc định `logs/compare_audit.log`). |
| `COMPARE_WRITE_DB` | Mặc định bật; đặt `0` / `false` / `no` / `off` → không insert bảng `compare_audit` (ví dụ chạy uvicorn tay không cần DB). |
| `COMPAREPDF_SKIP_DB_AUDIT` | Chỉ `test_local.py` set `=1` cho process con → không ghi DB khi test local. |

Nếu Postgres không chạy, `init_db()` chỉ log cảnh báo — API vẫn khởi động; từng request có thể báo lỗi khi ghi DB (được bắt trong router).

Ví dụ `DATABASE_URL` (tên DB mặc định trong `docker-compose.postgres.yml` là `comparepdf`):

```bash
DATABASE_URL=postgresql+psycopg://comparepdf_user:comparepdf_pass@localhost:5432/comparepdf
```

Chạy PostgreSQL local:

```bash
docker compose -f docker-compose.postgres.yml up -d
```

Xem lịch sử compare đã lưu trong DB:

```bash
curl "http://127.0.0.1:8000/audit-history?limit=20&offset=0"
```

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

### POST /signature_compare

So sánh 2 ảnh chữ ký dạng base64 (PoC step 1 theo `compare_signature.md`).

Request:

```json
{
  "signature_ref": "base64_or_data_url",
  "signature_test": "base64_or_data_url"
}
```

Response:

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

### POST /compare-pdf-sharepoint

Tải 2 file từ SharePoint rồi so sánh bằng cùng logic như `/compare-pdf`.

**Ràng buộc:** `location_a` và `location_b` phải trỏ tới file có tên kết thúc bằng `.pdf` (phần tên file sau `/` cuối). Nếu không → `400` với mô tả lỗi.

### GET /sharepoint/list-files và POST /sharepoint/list-files

Lấy danh sách file trong một folder SharePoint (qua `urlGetAllFilesNameSharePoint`). **GET** phù hợp thao tác chỉ đọc (query string). **POST** giữ lại vì gửi **JSON body** tiện khi `folder_location` dài hoặc nhiều field — chuẩn HTTP không khuyến nghị body cho GET.

**Ràng buộc (mặc định `strict_folder_rules: true`):** sau khi PA trả về, folder phải có **một hoặc hai** file **PDF**; 0 file, >2 file, hoặc có file không `.pdf` → `400` (giống `localPDF/` ở test local). Đặt `strict_folder_rules=false` (query hoặc JSON) nếu chỉ cần liệt kê đầy đủ.

**GET (khuyến nghị dùng `-G` + `--data-urlencode` cho khoảng trắng trong đường dẫn):**

```bash
curl -G "http://127.0.0.1:8000/sharepoint/list-files" \
  --data-urlencode "folder_location=Shared Documents/Contracts" \
  --data-urlencode "web_url=https://yourtenant.sharepoint.com/sites/yoursite" \
  --data-urlencode "typefile=pdf" \
  --data-urlencode "strict_folder_rules=true"
```

**POST (body JSON):**

```bash
curl -X POST http://127.0.0.1:8000/sharepoint/list-files \
  -H "Content-Type: application/json" \
  -d '{
    "web_url": "https://yourtenant.sharepoint.com/sites/yoursite",
    "folder_location": "Shared Documents/Contracts",
    "typefile": "pdf",
    "strict_folder_rules": true
  }'
```

Response:

```json
{
  "files": ["Original.pdf", "OriginalEdit.pdf"]
}
```

```bash
curl -X POST http://127.0.0.1:8000/compare-pdf-sharepoint \
  -H "Content-Type: application/json" \
  -d '{
    "web_url": "https://yourtenant.sharepoint.com/sites/yoursite",
    "location_a": "Shared Documents/Contracts/Original.pdf",
    "location_b": "Shared Documents/Contracts/OriginalEdit.pdf",
    "fetch_mode": "power_automate"
  }'
```

`fetch_mode` hỗ trợ:
- `power_automate` (khuyến nghị, theo hướng C# hiện tại)
- `rest` (gọi SharePoint REST trực tiếp)

### Response mẫu (`POST /compare-pdf` và compare SharePoint)

Mọi response so sánh đều có thêm `source_signature` và `target_signature` (phát hiện field chữ ký qua AcroForm; **không** xác minh mật mã). Chi tiết roadmap PKCS#7 / PAdES: [`docs/signature-step2-step3.md`](docs/signature-step2-step3.md).

**Khi 2 file giống nhau:**

```json
{
  "same": true,
  "source_file": "Original.pdf",
  "target_file": "OriginalEdit.pdf",
  "summary": {
    "total_pages_a": 3,
    "total_pages_b": 3,
    "total_differences": 0
  },
  "differences": [],
  "source_signature": {
    "has_digital_signature": false,
    "signature_count": 0,
    "field_names": []
  },
  "target_signature": {
    "has_digital_signature": false,
    "signature_count": 0,
    "field_names": []
  },
  "elapsed_ms": 18.23,
  "ai_summary": null
}
```

**Khi 2 file khác nhau:**

```json
{
  "same": false,
  "source_file": "Original.pdf",
  "target_file": "OriginalEdit.pdf",
  "summary": {
    "total_pages_a": 3,
    "total_pages_b": 3,
    "total_differences": 1
  },
  "differences": [
    {
      "page_a": 1,
      "page_b": 1,
      "added": "...SHARED [CONSTRUCTION] PARTICIPATION...",
      "removed": "...SHARED [COSDFDFTRUCTION] PARTICIPATION..."
    }
  ],
  "source_signature": {
    "has_digital_signature": false,
    "signature_count": 0,
    "field_names": []
  },
  "target_signature": {
    "has_digital_signature": false,
    "signature_count": 0,
    "field_names": []
  },
  "elapsed_ms": 27.41,
  "ai_summary": "Hai file khác nhau tại 1 vị trí chính..."
}
```

## Test local

Test nhanh không cần curl hay Swagger — script tự khởi động server, gọi API, lưu kết quả rồi tắt server. Process uvicorn con có **`COMPAREPDF_SKIP_DB_AUDIT=1`** nên **không insert** PostgreSQL (tránh làm bẩn DB khi dev).

**Chọn file trực tiếp (interactive):**

macOS / Linux:

```bash
source .venv/bin/activate
python test_local.py
```

Windows:

```cmd
.venv\Scripts\activate
python test_local.py
```

Với interactive, `localPDF/` phải tồn tại; trong thư mục **chỉ** được có file **PDF** (đuôi `.pdf`); **một hoặc hai** file (không có file nào hoặc hơn hai file → báo lỗi). Khi truyền hai đường dẫn trên dòng lệnh, cả hai cũng phải là `.pdf`.

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
python test_local.py --auto    # tìm tất cả cặp _a/_b
```

Windows:

```cmd
.venv\Scripts\activate
python generate_test_pdfs.py
python test_local.py --auto
```

## Cấu trúc project

```
ComparePDF/
├── .env.example                 # Mẫu biến môi trường (copy → .env)
├── Dockerfile                   # Image API production
├── .dockerignore
├── docker-compose.yml           # API + Postgres (deploy)
├── docker-compose.postgres.yml  # Chỉ Postgres 16 (dev / DB riêng)
├── requirements.txt
├── README.md
├── docs/
│   └── signature-step2-step3.md # Ghi chú triển khai verify PKCS#7 / PAdES (tương lai)
├── generate_test_pdfs.py        # Tạo PDF mẫu vào localPDF/
├── test_local.py                # Test qua HTTP: khởi động uvicorn, gọi /compare-pdf, output/
├── localPDF/                    # PDF dùng cho test interactive / --auto (không bắt buộc commit)
├── logs/                        # compare_audit.log (mặc định)
├── output/                      # JSON kết quả từ test_local
└── app/
    ├── main.py                  # FastAPI app, startup init_db
    ├── config.py                # load_dotenv, OPENAI, SharePoint, DATABASE_URL, audit flags
    ├── db.py                    # SQLAlchemy engine, SessionLocal, create_all (lỗi DB không chặn startup)
    ├── models.py                # ORM CompareAudit
    ├── router.py                # Tất cả route: compare, SharePoint, audit-history
    ├── schemas.py               # Pydantic models (CompareResponse, SharePoint*, SignatureInfo, …)
    ├── exceptions.py            # PDFError, SharePointError, SharePointFolderRuleError, …
    └── services/
        ├── ai_summary.py          # Tóm tắt OpenAI (tuỳ chọn)
        ├── audit_service.py       # Ghi file log + insert DB
        ├── comparator.py        # So khác text (word-level + document-level)
        ├── pdf_reader.py        # PyMuPDF: trích text theo trang
        ├── pdf_signature.py     # Step 1: phát hiện field ký (pypdf); stub step 2/3
        ├── sharepoint_client.py # List + download qua Power Automate / REST; validate folder/paths
        └── text_processor.py    # Chuẩn hoá text trước khi diff
```

## Tech stack

- **Docker / Compose** — Image `Dockerfile`, stack `docker-compose.yml` (API + Postgres)
- **FastAPI** — REST API, OpenAPI `/docs`
- **Uvicorn** — ASGI server
- **Pydantic v2** — Schema request/response
- **PyMuPDF** — Trích text từ PDF
- **pypdf** — Đọc AcroForm / field chữ ký (bước 1)
- **python-multipart** — Upload file
- **requests** — SharePoint / Power Automate
- **OpenAI** (tuỳ chọn) — `ai_summary`
- **SQLAlchemy + psycopg** — PostgreSQL audit
- **python-dotenv** — `.env`
- **difflib** (stdlib) — So khác chuỗi
