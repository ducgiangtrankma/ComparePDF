from pydantic import BaseModel
from datetime import datetime


class DiffSummary(BaseModel):
    total_pages_a: int
    total_pages_b: int
    total_differences: int


class WordDifference(BaseModel):
    page_a: int | None
    page_b: int | None
    added: str
    removed: str


class CompareResult(BaseModel):
    same: bool
    summary: DiffSummary
    differences: list[WordDifference]


class CompareResponse(CompareResult):
    source_file: str
    target_file: str
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
    web_url: str | None = None
    folder_location: str
    typefile: str = "pdf"


class SharePointListFilesResponse(BaseModel):
    files: list[str]


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
