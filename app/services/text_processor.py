import re
import unicodedata


def normalize_whitespace(text: str) -> str:
    """Replace all unicode whitespace variants with standard ASCII equivalents."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\xa0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text


def to_words(text: str) -> list[str]:
    """Collapse all whitespace and split text into a flat word list.

    This eliminates line-wrapping and paragraph-spacing differences entirely,
    so only real word-level content changes are detected.
    """
    text = normalize_whitespace(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.split(" ") if text else []


def strip_page_number(words: list[str]) -> list[str]:
    """Remove a leading standalone page number (e.g. '1', '2') if present."""
    if words and words[0].isdigit():
        return words[1:]
    return words
