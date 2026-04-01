"""Optional OpenAI summarization of PDF compare results."""

import json
import logging
from typing import Any

from app.schemas import CompareResult

logger = logging.getLogger(__name__)

MAX_PAYLOAD_CHARS = 48_000


def _result_to_payload(result: CompareResult, name_a: str, name_b: str) -> str:
    data: dict[str, Any] = {
        "file_a": name_a,
        "file_b": name_b,
        "same": result.same,
        "summary": result.summary.model_dump(),
        "differences": [d.model_dump() for d in result.differences],
    }
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if len(text) > MAX_PAYLOAD_CHARS:
        text = text[:MAX_PAYLOAD_CHARS] + "\n… [truncated]"
    return text


async def summarize_compare_result(
    result: CompareResult,
    name_a: str,
    name_b: str,
) -> str | None:
    """Return a short human-readable summary in Vietnamese, or None if skipped."""
    from app.config import OPENAI_API_KEY, OPENAI_MODEL

    if not OPENAI_API_KEY:
        return None

    try:
        from openai import AsyncOpenAI
    except ImportError:
        logger.warning("openai package not installed; skip AI summary")
        return None

    payload = _result_to_payload(result, name_a, name_b)

    system = (
        "Bạn là trợ lý phân tích tài liệu. Dựa trên JSON so sánh hai file PDF, "
        "hãy viết bản tóm tắt ngắn gọn, dễ hiểu bằng tiếng Việt cho người dùng không chuyên. "
        "Nêu rõ có khác biệt hay không, các thay đổi chính (nếu có), và gợi ý trang liên quan nếu có. "
        "Không lặp lại nguyên văn toàn bộ diff; chỉ tóm ý. "
        "Nếu không có khác biệt nội dung, nói rõ hai tài liệu trùng khớp về text."
    )

    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    chat = await client.chat.completions.create(
        model=OPENAI_MODEL,
        temperature=0.2,
        max_tokens=1200,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": payload},
        ],
    )

    choice = chat.choices[0].message.content
    return choice.strip() if choice else None
