import difflib
import re
from datetime import datetime, UTC

import fitz

from app.schemas import (
    AnchorBox,
    CompareResponse,
    CompareResponseV2,
    CompareV2Difference,
    CompareV2FileInfo,
    CompareV2Links,
    CompareV2SignatureItem,
    CompareV2Signatures,
    CompareV2Summary,
    CompareV2Warning,
)
from app.services.text_processor import normalize_whitespace, to_words

_CORE_RE = re.compile(r"\[(.+?)\]")


def _extract_core(snippet: str) -> str:
    if not snippet:
        return ""
    match = _CORE_RE.search(snippet)
    return match.group(1) if match else snippet


def _norm_token(text: str) -> str:
    return normalize_whitespace(text).strip()


def _classify_diff(removed: str, added: str) -> str:
    if removed and added:
        return "text_replace"
    if removed:
        return "text_delete"
    return "text_insert"


def _estimate_confidence(removed: str, added: str) -> float:
    if removed and added:
        ratio = difflib.SequenceMatcher(None, removed, added).ratio()
        return round(max(0.5, ratio), 2)
    return 0.9


def _extract_page_tokens(content: bytes) -> tuple[list[list[dict]], int]:
    page_tokens: list[list[dict]] = []
    doc = fitz.open(stream=content, filetype="pdf")
    try:
        for page in doc:
            width = float(page.rect.width) or 1.0
            height = float(page.rect.height) or 1.0
            words = page.get_text("words")
            tokens: list[dict] = []
            for item in words:
                x0, y0, x1, y1, word = item[:5]
                normalized = _norm_token(str(word))
                if not normalized:
                    continue
                tokens.append(
                    {
                        "word": normalized,
                        "rect": (
                            float(x0),
                            float(y0),
                            float(x1),
                            float(y1),
                        ),
                        "page_size": (width, height),
                    }
                )
            page_tokens.append(tokens)
    finally:
        doc.close()
    return page_tokens, len(page_tokens)


def _build_anchor(tokens: list[dict], query: str) -> AnchorBox | None:
    query_tokens = [_norm_token(t) for t in to_words(query) if _norm_token(t)]
    if not query_tokens:
        return None
    if not tokens:
        return None

    words = [token["word"] for token in tokens]
    size = len(query_tokens)
    start_idx = -1
    for i in range(0, max(0, len(words) - size + 1)):
        if words[i : i + size] == query_tokens:
            start_idx = i
            break

    if start_idx < 0:
        for i, word in enumerate(words):
            if query_tokens[0] in word:
                start_idx = i
                size = 1
                break

    if start_idx < 0:
        return None

    selected = tokens[start_idx : start_idx + size]
    x0 = min(t["rect"][0] for t in selected)
    y0 = min(t["rect"][1] for t in selected)
    x1 = max(t["rect"][2] for t in selected)
    y1 = max(t["rect"][3] for t in selected)
    width, height = selected[0]["page_size"]

    return AnchorBox(
        x=round(x0 / width, 6),
        y=round(y0 / height, 6),
        width=round((x1 - x0) / width, 6),
        height=round((y1 - y0) / height, 6),
    )


def _build_warnings(compare_response: CompareResponse) -> list[CompareV2Warning]:
    suspicious_pages_a = [
        item.page
        for item in compare_response.source_hand_signature
        if (item.decision or "").lower() == "suspicious"
    ]
    suspicious_pages_b = [
        item.page
        for item in compare_response.target_hand_signature
        if (item.decision or "").lower() == "suspicious"
    ]
    warnings: list[CompareV2Warning] = []
    if suspicious_pages_a:
        warnings.append(
            CompareV2Warning(
                code="SUSPICIOUS_SIGNATURE_SOURCE",
                message="Suspicious signature pages found in source file",
                pages=suspicious_pages_a,
            )
        )
    if suspicious_pages_b:
        warnings.append(
            CompareV2Warning(
                code="SUSPICIOUS_SIGNATURE_TARGET",
                message="Suspicious signature pages found in target file",
                pages=suspicious_pages_b,
            )
        )
    return warnings


def build_compare_response_v2(
    compare_response: CompareResponse,
    content_a: bytes,
    content_b: bytes,
    source_path: str,
    target_path: str,
    request_id: str,
) -> CompareResponseV2:
    tokens_a, pages_a = _extract_page_tokens(content_a)
    tokens_b, pages_b = _extract_page_tokens(content_b)

    v2_diffs: list[CompareV2Difference] = []
    for idx, diff in enumerate(compare_response.differences, start=1):
        removed_core = _extract_core(diff.removed)
        added_core = _extract_core(diff.added)
        page_a = diff.page_a
        page_b = diff.page_b
        anchor_a = None
        anchor_b = None

        if page_a and removed_core and 1 <= page_a <= len(tokens_a):
            anchor_a = _build_anchor(tokens_a[page_a - 1], removed_core)
        if page_b and added_core and 1 <= page_b <= len(tokens_b):
            anchor_b = _build_anchor(tokens_b[page_b - 1], added_core)

        v2_diffs.append(
            CompareV2Difference(
                diff_id=f"d_{idx:04d}",
                type=_classify_diff(removed_core, added_core),
                page_a=page_a,
                page_b=page_b,
                removed=removed_core,
                added=added_core,
                confidence=_estimate_confidence(removed_core, added_core),
                anchor_a=anchor_a,
                anchor_b=anchor_b,
            )
        )

    signatures = CompareV2Signatures(
        source_hand_signature=[
            CompareV2SignatureItem(
                page=item.page,
                best_score=item.best_score,
                decision=item.decision,
                matched_reference=item.matched_reference,
            )
            for item in compare_response.source_hand_signature
        ],
        target_hand_signature=[
            CompareV2SignatureItem(
                page=item.page,
                best_score=item.best_score,
                decision=item.decision,
                matched_reference=item.matched_reference,
            )
            for item in compare_response.target_hand_signature
        ],
    )

    return CompareResponseV2(
        generated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        request_id=request_id,
        source_file=CompareV2FileInfo(
            name=compare_response.source_file,
            path=source_path,
            pages=pages_a,
        ),
        target_file=CompareV2FileInfo(
            name=compare_response.target_file,
            path=target_path,
            pages=pages_b,
        ),
        summary=CompareV2Summary(
            total_pages_a=compare_response.summary.total_pages_a,
            total_pages_b=compare_response.summary.total_pages_b,
            total_differences=compare_response.summary.total_differences,
            has_digital_signature_a=compare_response.source_signature.has_digital_signature,
            has_digital_signature_b=compare_response.target_signature.has_digital_signature,
        ),
        differences=v2_diffs,
        signatures=signatures,
        warnings=_build_warnings(compare_response),
        links=CompareV2Links(diff_report_url=None),
    )
