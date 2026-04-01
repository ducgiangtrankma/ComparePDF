import difflib
import re
from bisect import bisect_right
from collections import Counter

from app.schemas import CompareResult, DiffSummary, WordDifference
from app.services.text_processor import strip_page_number, to_words

CONTEXT_WORDS = 5
_BRACKET_RE = re.compile(r"\[(.+?)\]")


def _build_doc_words(pages: list[str]) -> tuple[list[str], list[int]]:
    """Merge all pages into a single word list with page boundary tracking.

    Returns (words, boundaries) where boundaries[i] is the cumulative
    word count up to and including page i.
    """
    all_words: list[str] = []
    boundaries: list[int] = []

    for page_text in pages:
        page_words = strip_page_number(to_words(page_text))
        all_words.extend(page_words)
        boundaries.append(len(all_words))

    return all_words, boundaries


def _word_index_to_page(index: int, boundaries: list[int]) -> int:
    """Map a word index back to its 1-based page number."""
    return bisect_right(boundaries, index) + 1


def _build_snippet(words: list[str], start: int, end: int) -> str:
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


def _extract_core(snippet: str) -> str:
    """Extract the changed text inside [...] from a snippet."""
    m = _BRACKET_RE.search(snippet)
    return m.group(1) if m else ""


def _cancel_moved_text(diffs: list[WordDifference]) -> list[WordDifference]:
    """Remove diffs where the same text appears as both added and removed.

    When page breaks differ, identical text can appear as "deleted" at one
    position and "inserted" at another. These pairs are not real content
    changes — just text that moved across page boundaries.
    """
    added_cores: Counter[str] = Counter()
    removed_cores: Counter[str] = Counter()

    for d in diffs:
        if d.added:
            core = _extract_core(d.added)
            if core:
                added_cores[core] += 1
        if d.removed:
            core = _extract_core(d.removed)
            if core:
                removed_cores[core] += 1

    moved = set()
    for text in added_cores:
        if text in removed_cores:
            moved.add(text)

    if not moved:
        return diffs

    result: list[WordDifference] = []
    for d in diffs:
        a_core = _extract_core(d.added) if d.added else ""
        r_core = _extract_core(d.removed) if d.removed else ""

        a_is_moved = a_core in moved
        r_is_moved = r_core in moved

        if a_is_moved and r_is_moved:
            continue
        if a_is_moved and not d.removed:
            continue
        if r_is_moved and not d.added:
            continue

        new_added = "" if a_is_moved else d.added
        new_removed = "" if r_is_moved else d.removed

        if new_added or new_removed:
            result.append(WordDifference(
                page_a=d.page_a,
                page_b=d.page_b,
                added=new_added,
                removed=new_removed,
            ))

    return result


def compare_pages(pages_a: list[str], pages_b: list[str]) -> CompareResult:
    """Compare two documents at the word level, ignoring page boundaries."""
    words_a, bounds_a = _build_doc_words(pages_a)
    words_b, bounds_b = _build_doc_words(pages_b)

    raw_diffs: list[WordDifference] = []

    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
        None, words_a, words_b
    ).get_opcodes():
        if tag == "equal":
            continue

        page_a = _word_index_to_page(i1, bounds_a) if i1 < len(words_a) else None
        page_b = _word_index_to_page(j1, bounds_b) if j1 < len(words_b) else None

        removed = _build_snippet(words_a, i1, i2) if tag in ("replace", "delete") else ""
        added = _build_snippet(words_b, j1, j2) if tag in ("replace", "insert") else ""

        raw_diffs.append(WordDifference(
            page_a=page_a, page_b=page_b,
            removed=removed, added=added,
        ))

    differences = _cancel_moved_text(raw_diffs)

    summary = DiffSummary(
        total_pages_a=len(pages_a),
        total_pages_b=len(pages_b),
        total_differences=len(differences),
    )

    return CompareResult(
        same=len(differences) == 0,
        summary=summary,
        differences=differences,
    )
