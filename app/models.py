from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _json_type():
    try:
        return JSONB
    except Exception:
        return JSON


class CompareAudit(Base):
    __tablename__ = "compare_audit"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_file: Mapped[str] = mapped_column(String(512), nullable=False)
    target_file: Mapped[str] = mapped_column(String(512), nullable=False)
    same: Mapped[bool] = mapped_column(Boolean, nullable=False)
    total_pages_a: Mapped[int] = mapped_column(Integer, nullable=False)
    total_pages_b: Mapped[int] = mapped_column(Integer, nullable=False)
    total_differences: Mapped[int] = mapped_column(Integer, nullable=False)
    elapsed_ms: Mapped[float] = mapped_column(Float, nullable=False)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_json: Mapped[dict] = mapped_column(_json_type(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), default=datetime.utcnow, nullable=False
    )
