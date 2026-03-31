import difflib
from itertools import zip_longest

from app.schemas import CompareResult, DiffSummary, PageDifference
from app.services.text_processor import strip_page_number, to_words

CONTEXT_WORDS = 5


def _build_snippet(words: list[str], start: int, end: int) -> str:
    """Build a readable snippet with surrounding context."""
    ctx_start = max(0, start - CONTEXT_WORDS)
    ctx_end = min(len(words), end + CONTEXT_WORDS)

    prefix = "..." if ctx_start > 0 else ""
    suffix = "..." if ctx_end < len(words) else ""

    before = " ".join(words[ctx_start:start])
    changed = " ".join(words[start:end])
    after = " ".join(words[end:ctx_end])

    parts = []
    if before:
        parts.append(before)
    parts.append(f"[{changed}]")
    if after:
        parts.append(after)

    return f"{prefix}{' '.join(parts)}{suffix}"


def _diff_words(
    text_a: str, text_b: str,
) -> tuple[list[str], list[str]]:
    """Compare two page texts word-by-word.

    Returns (added, removed) with context snippets around each change.
    """
    words_a = strip_page_number(to_words(text_a))
    words_b = strip_page_number(to_words(text_b))

    added: list[str] = []
    removed: list[str] = []

    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
        None, words_a, words_b
    ).get_opcodes():
        if tag == "replace":
            removed.append(_build_snippet(words_a, i1, i2))
            added.append(_build_snippet(words_b, j1, j2))
        elif tag == "delete":
            removed.append(_build_snippet(words_a, i1, i2))
        elif tag == "insert":
            added.append(_build_snippet(words_b, j1, j2))

    return added, removed


def compare_pages(pages_a: list[str], pages_b: list[str]) -> CompareResult:
    """Compare two lists of page texts and produce a structured diff result."""
    differences: list[PageDifference] = []

    for idx, (text_a, text_b) in enumerate(
        zip_longest(pages_a, pages_b, fillvalue="")
    ):
        words_a = strip_page_number(to_words(text_a))
        words_b = strip_page_number(to_words(text_b))

        if words_a == words_b:
            continue

        added, removed = _diff_words(text_a, text_b)
        differences.append(
            PageDifference(page=idx + 1, added=added, removed=removed)
        )

    summary = DiffSummary(
        total_pages_a=len(pages_a),
        total_pages_b=len(pages_b),
        different_pages=len(differences),
    )

    return CompareResult(
        same=len(differences) == 0,
        summary=summary,
        differences=differences,
    )
