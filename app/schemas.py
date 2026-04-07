from datetime import datetime

from pydantic import BaseModel, Field


class DiffSummary(BaseModel):
    total_pages_a: int
    total_pages_b: int
    total_differences: int


class WordDifference(BaseModel):
    page_a: int | None
    page_b: int | None
    added: str
    removed: str


class SignatureInfo(BaseModel):
    """AcroForm-based presence of signature fields (not cryptographic validation)."""

    has_digital_signature: bool
    signature_count: int
    field_names: list[str] = []


class CompareResult(BaseModel):
    same: bool
    summary: DiffSummary
    differences: list[WordDifference]


class CompareResponse(CompareResult):
    source_file: str
    target_file: str
    source_signature: SignatureInfo
    target_signature: SignatureInfo
    elapsed_ms: float
    ai_summary: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "same": False,
                    "summary": {
                        "total_pages_a": 3,
                        "total_pages_b": 3,
                        "total_differences": 2,
                    },
                    "differences": [
                        {
                            "page_a": 1,
                            "page_b": 1,
                            "removed": "...SHARED [COSDFDFTRUCTION] PARTICIPATION...",
                            "added": "...SHARED [CONSTRUCTION] PARTICIPATION...",
                        }
                    ],
                    "source_file": "Original.pdf",
                    "target_file": "OriginalEdit.pdf",
                    "source_signature": {
                        "has_digital_signature": False,
                        "signature_count": 0,
                        "field_names": [],
                    },
                    "target_signature": {
                        "has_digital_signature": False,
                        "signature_count": 0,
                        "field_names": [],
                    },
                    "elapsed_ms": 123.45,
                    "ai_summary": "Hai file khác nhau ở từ CONSTRUCTION...",
                }
            ]
        }
    }


class SharePointCompareRequest(BaseModel):
    web_url: str | None = None
    location_a: str
    location_b: str
    fetch_mode: str | None = None


class SharePointListFilesRequest(BaseModel):
    web_url: str | None = Field(
        default=None,
        description="SharePoint site URL; nếu bỏ trống dùng SHAREPOINT_WEB_URL trong .env.",
    )
    folder_location: str = Field(
        ...,
        description="Đường dẫn folder trong site (vd. Shared Documents/Contracts).",
    )
    typefile: str = Field(
        default="pdf",
        description="Lọc gửi xuống Power Automate (thường pdf).",
    )
    strict_folder_rules: bool = Field(
        default=True,
        description=(
            "Nếu true: sau khi PA trả về, chỉ chấp nhận đúng 1–2 file PDF trong folder; "
            "0 file, >2 file, hoặc file không .pdf → 400. "
            "Nếu false: trả về danh sách gốc (để duyệt folder nhiều file)."
        ),
    )


class SharePointListFilesResponse(BaseModel):
    files: list[str] = Field(description="Tên file (hoặc đường dẫn tương đối) sau khi lọc.")


class SignatureCompareRequest(BaseModel):
    signature_ref: str = Field(
        ...,
        description="Base64 ảnh chữ ký mẫu (PNG/JPG), có thể là data URL hoặc raw base64.",
    )
    signature_test: str = Field(
        ...,
        description="Base64 ảnh chữ ký cần so sánh (PNG/JPG), có thể là data URL hoặc raw base64.",
    )


class SignatureCompareComponents(BaseModel):
    overlap_score: float
    shape_score: float
    projection_score: float


class SignatureCompareResponse(BaseModel):
    final_score: float
    decision: str
    components: SignatureCompareComponents


class HandSignaturePageResult(BaseModel):
    page: int
    has_signature: bool
    best_score: float
    decision: str | None = None
    bbox: tuple[int, int, int, int] | None = None
    components: SignatureCompareComponents | None = None


class HandSignatureCheckResponse(BaseModel):
    pages_a: list[HandSignaturePageResult]
    pages_b: list[HandSignaturePageResult]


class CompareAuditItem(BaseModel):
    id: int
    source_file: str
    target_file: str
    same: bool
    total_differences: int
    elapsed_ms: float
    created_at: datetime


class CompareAuditHistoryResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[CompareAuditItem]
