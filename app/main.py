from fastapi import FastAPI

import app.config  # noqa: F401 — load .env and env vars before routes

from app.db import init_db
from app.router import router

_OPENAPI_DESCRIPTION = """
So sánh nội dung **text hiển thị** giữa hai PDF (word-level diff), kèm tóm tắt AI tùy chọn.

**Bổ sung:** phát hiện trường ký số (AcroForm, không xác thực mật mã), phát hiện/so khớp chữ ký tay so với mẫu,
và tích hợp **SharePoint** (tải file qua Power Automate).

**Lưu ý:** PDF scan/ảnh không có text layer có thể không so sánh được nội dung chữ.
"""

app = FastAPI(
    title="PDF Compare API",
    description=_OPENAPI_DESCRIPTION.strip(),
    version="1.0.0",
    openapi_tags=[
        {
            "name": "compare",
            "description": "Upload hoặc SharePoint: so sánh hai PDF, trả diff + chữ ký số/tay + audit log.",
        },
        {
            "name": "sharepoint",
            "description": "Liệt kê file trong folder SharePoint (GET/POST).",
        },
        {
            "name": "audit",
            "description": "Lịch sử so sánh đã lưu (phân trang).",
        },
        {
            "name": "signatures",
            "description": "So sánh hai ảnh chữ ký base64 (PoC) hoặc phát hiện chữ ký tay trên PDF.",
        },
    ],
)

app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
