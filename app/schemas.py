from datetime import datetime

from pydantic import BaseModel, Field


class DiffSummary(BaseModel):
    total_pages_a: int = Field(description="Số trang đã đọc từ PDF A.")
    total_pages_b: int = Field(description="Số trang đã đọc từ PDF B.")
    total_differences: int = Field(description="Tổng số khác biệt word-level (theo engine hiện tại).")


class WordDifference(BaseModel):
    page_a: int | None = Field(description="Số trang tương ứng bên A (1-based), null nếu không áp dụng.")
    page_b: int | None = Field(description="Số trang tương ứng bên B (1-based), null nếu không áp dụng.")
    added: str = Field(description="Đoạn text được thêm / xuất hiện ở B.")
    removed: str = Field(description="Đoạn text bị xóa / chỉ còn ở A.")


class SignatureInfo(BaseModel):
    """AcroForm-based presence of signature fields (not cryptographic validation)."""

    has_digital_signature: bool = Field(description="Có ít nhất một trường ký (widget) trên PDF.")
    signature_count: int = Field(description="Số trường ký phát hiện được.")
    field_names: list[str] = Field(default_factory=list, description="Tên trường ký (AcroForm), có thể rỗng.")


class SignatureCompareComponents(BaseModel):
    overlap_score: float = Field(description="Điểm chồng lấp (0–1).")
    shape_score: float = Field(description="Điểm hình dạng (0–1).")
    projection_score: float = Field(description="Điểm chiếu/projection (0–1).")


class HandSignaturePageResult(BaseModel):
    page: int = Field(description="Số trang 1-based.")
    has_signature: bool = Field(description="Phát hiện vùng giống chữ ký trong ROI.")
    best_score: float = Field(description="Điểm khớp tốt nhất với mẫu tham chiếu.")
    decision: str | None = Field(default=None, description="Nhãn quyết định từ engine (nếu có).")
    bbox: tuple[int, int, int, int] | None = Field(
        default=None,
        description="Hộp giới hạn chữ ký trên ảnh render (x0, y0, x1, y1) pixel.",
    )
    components: SignatureCompareComponents | None = Field(
        default=None,
        description="Chi tiết điểm thành phần khi có.",
    )
    matched_reference: str | None = Field(
        default=None,
        description="Tên file mẫu khớp nhất (khi dùng nhiều candidate).",
    )


class CompareResult(BaseModel):
    same: bool = Field(description="True nếu engine coi hai bản text tương đương (theo quy tắc nội bộ).")
    summary: DiffSummary
    differences: list[WordDifference]


class CompareResponse(CompareResult):
    source_file: str = Field(description="Tên hoặc đường dẫn hiển thị cho PDF A.")
    target_file: str = Field(description="Tên hoặc đường dẫn hiển thị cho PDF B.")
    source_signature: SignatureInfo
    target_signature: SignatureInfo
    source_hand_signature: list[HandSignaturePageResult] = Field(
        default_factory=list,
        description="Theo từng trang: phát hiện/so khớp chữ ký tay cho file A (mẫu server hoặc SharePoint).",
    )
    target_hand_signature: list[HandSignaturePageResult] = Field(
        default_factory=list,
        description="Tương tự `source_hand_signature` cho file B.",
    )
    elapsed_ms: float = Field(description="Thời gian xử lý so sánh (ms), làm tròn.")
    ai_summary: str | None = Field(
        default=None,
        description="Tóm tắt ngôn ngữ tự nhiên về khác biệt (nếu dịch vụ AI khả dụng).",
    )

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
                    "source_hand_signature": [],
                    "target_hand_signature": [],
                    "elapsed_ms": 123.45,
                    "ai_summary": "Hai file khác nhau ở từ CONSTRUCTION...",
                }
            ]
        }
    }


class SharePointCompareRequest(BaseModel):
    web_url: str | None = Field(
        default=None,
        description="URL site SharePoint; null dùng biến môi trường mặc định.",
    )
    location_a: str = Field(..., description="Đường dẫn file PDF A trên site (theo convention PA).")
    location_b: str = Field(..., description="Đường dẫn file PDF B trên site.")
    signature_location: str | None = Field(
        default=None,
        description=(
            "Đường dẫn file/folder chữ ký mẫu trên SharePoint. "
            "Nếu là folder, hệ thống lấy tất cả ảnh .png/.jpg/.jpeg trong folder."
        ),
    )
    fetch_mode: str | None = Field(
        default=None,
        description="Tuỳ chọn gửi xuống tầng tải file (nếu backend/PA hỗ trợ).",
    )


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


class SignatureCompareResponse(BaseModel):
    final_score: float = Field(description="Điểm tổng hợp sau khi kết hợp các thành phần.")
    decision: str = Field(description="Kết luận ngắn (vd. match / no_match tùy ngưỡng).")
    components: SignatureCompareComponents


class HandSignatureCheckResponse(BaseModel):
    pages_a: list[HandSignaturePageResult] = Field(description="Kết quả theo trang cho PDF A.")
    pages_b: list[HandSignaturePageResult] = Field(description="Kết quả theo trang cho PDF B.")


class CompareAuditItem(BaseModel):
    id: int = Field(description="Khóa bản ghi audit.")
    source_file: str
    target_file: str
    same: bool
    total_differences: int
    elapsed_ms: float
    created_at: datetime = Field(description="Thời điểm ghi nhận (UTC hoặc theo DB).")


class CompareAuditHistoryResponse(BaseModel):
    total: int = Field(description="Tổng số bản ghi thỏa điều kiện (không chỉ trang hiện tại).")
    limit: int = Field(description="Giới hạn đã yêu cầu.")
    offset: int = Field(description="Offset đã yêu cầu.")
    items: list[CompareAuditItem]
