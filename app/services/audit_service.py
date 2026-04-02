import json
import logging
from pathlib import Path

from sqlalchemy import desc

from app.config import COMPARE_LOG_PATH
from app.db import SessionLocal
from app.models import CompareAudit
from app.schemas import CompareResponse

logger = logging.getLogger(__name__)


def _ensure_file_logger() -> logging.Logger:
    log_path = Path(COMPARE_LOG_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    audit_logger = logging.getLogger("compare_audit")
    if not audit_logger.handlers:
        handler = logging.FileHandler(log_path, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        audit_logger.addHandler(handler)
        audit_logger.setLevel(logging.INFO)
        audit_logger.propagate = False
    return audit_logger


def write_compare_log(response: CompareResponse) -> None:
    audit_logger = _ensure_file_logger()
    payload = {
        "source_file": response.source_file,
        "target_file": response.target_file,
        "same": response.same,
        "summary": response.summary.model_dump(),
        "elapsed_ms": response.elapsed_ms,
    }
    audit_logger.info(json.dumps(payload, ensure_ascii=False))


def write_compare_db(response: CompareResponse) -> None:
    if SessionLocal is None:
        return

    row = CompareAudit(
        source_file=response.source_file,
        target_file=response.target_file,
        same=response.same,
        total_pages_a=response.summary.total_pages_a,
        total_pages_b=response.summary.total_pages_b,
        total_differences=response.summary.total_differences,
        elapsed_ms=response.elapsed_ms,
        ai_summary=response.ai_summary,
        result_json=response.model_dump(mode="json"),
    )

    session = SessionLocal()
    try:
        session.add(row)
        session.commit()
    finally:
        session.close()


def get_compare_history(limit: int = 20, offset: int = 0) -> tuple[int, list[CompareAudit]]:
    if SessionLocal is None:
        return 0, []

    session = SessionLocal()
    try:
        total = session.query(CompareAudit).count()
        rows = (
            session.query(CompareAudit)
            .order_by(desc(CompareAudit.id))
            .offset(offset)
            .limit(limit)
            .all()
        )
        return total, rows
    finally:
        session.close()
