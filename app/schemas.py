from pydantic import BaseModel


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
                    "elapsed_ms": 123.45,
                    "ai_summary": "Hai file khác nhau ở từ CONSTRUCTION...",
                }
            ]
        }
    }
