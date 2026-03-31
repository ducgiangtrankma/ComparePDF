from pydantic import BaseModel


class DiffSummary(BaseModel):
    total_pages_a: int
    total_pages_b: int
    different_pages: int


class PageDifference(BaseModel):
    page: int
    added: list[str]
    removed: list[str]


class CompareResponse(BaseModel):
    same: bool
    summary: DiffSummary
    differences: list[PageDifference]

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "same": False,
                    "summary": {
                        "total_pages_a": 3,
                        "total_pages_b": 3,
                        "different_pages": 1,
                    },
                    "differences": [
                        {
                            "page": 2,
                            "added": ["New line added in file B"],
                            "removed": ["Original line from file A"],
                        }
                    ],
                }
            ]
        }
    }
