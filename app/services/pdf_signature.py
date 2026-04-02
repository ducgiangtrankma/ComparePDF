"""PDF digital signature: step 1 = AcroForm/field detection; steps 2–3 = stubs (not wired)."""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Any

from pypdf import PdfReader
from pypdf.generic import IndirectObject

logger = logging.getLogger(__name__)


def _deref(obj: Any, reader: PdfReader) -> Any:
    if isinstance(obj, IndirectObject):
        return obj.get_object()
    return obj


def _field_name(field: Any) -> str | None:
    t = field.get("/T")
    if t is None:
        return None
    s = str(t)
    return s if s else None


def _is_signature_field(field: Any, reader: PdfReader) -> bool:
    field = _deref(field, reader)
    if not isinstance(field, dict):
        return False
    ft = field.get("/FT")
    if ft is not None and str(ft) == "/Sig":
        return True
    v = field.get("/V")
    if v is None:
        return False
    v = _deref(v, reader)
    if not isinstance(v, dict):
        return False
    if v.get("/Type") is not None and str(v.get("/Type")) == "/Sig":
        return True
    return "/Contents" in v and "/ByteRange" in v


def _collect_signature_fields(
    field_list: list[Any] | None, reader: PdfReader, out: list[str]
) -> None:
    if not field_list:
        return
    for ref in field_list:
        field = _deref(ref, reader)
        if not isinstance(field, dict):
            continue
        kids = field.get("/Kids")
        if kids:
            kids = _deref(kids, reader)
            if isinstance(kids, list):
                _collect_signature_fields(kids, reader, out)
                continue
        if _is_signature_field(field, reader):
            out.append(_field_name(field) or "(unnamed)")


def detect_digital_signatures(pdf_bytes: bytes) -> dict[str, Any]:
    """
    Step 1: detect signature fields / signature dictionaries via AcroForm (no crypto verify).
    Returns: has_digital_signature, signature_count, field_names.
    """
    has_sig = False
    count = 0
    field_names: list[str] = []
    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=False)
        root = reader.trailer.get("/Root")
        if root is None:
            return {
                "has_digital_signature": False,
                "signature_count": 0,
                "field_names": [],
            }
        root = _deref(root, reader)
        if not isinstance(root, dict) or "/AcroForm" not in root:
            return {
                "has_digital_signature": False,
                "signature_count": 0,
                "field_names": [],
            }
        acro = _deref(root["/AcroForm"], reader)
        if not isinstance(acro, dict):
            return {
                "has_digital_signature": False,
                "signature_count": 0,
                "field_names": [],
            }
        fields = acro.get("/Fields")
        if fields is None:
            return {
                "has_digital_signature": False,
                "signature_count": 0,
                "field_names": [],
            }
        fields = _deref(fields, reader)
        if not isinstance(fields, list):
            return {
                "has_digital_signature": False,
                "signature_count": 0,
                "field_names": [],
            }
        _collect_signature_fields(fields, reader, field_names)
        count = len(field_names)
        has_sig = count > 0
    except Exception as exc:
        logger.debug("Signature detection failed: %s", exc)
        return {
            "has_digital_signature": False,
            "signature_count": 0,
            "field_names": [],
        }
    return {
        "has_digital_signature": has_sig,
        "signature_count": count,
        "field_names": field_names,
    }


def verify_pkcs7_detached(
    signed_pdf_bytes: bytes,
    *,
    revision_index: int | None = None,
) -> dict[str, Any]:
    """
    Step 2 (stub): detached PKCS#7 cryptographic verification — not implemented; do not call from API.
    """
    return {"implemented": False, "reason": "pkcs7 verification not wired"}


def verify_pades_advanced(
    signed_pdf_bytes: bytes,
    *,
    trust_roots: list[str] | None = None,
) -> dict[str, Any]:
    """
    Step 3 (stub): PAdES / LTV / pyHanko-style checks — not implemented; do not call from API.
    """
    return {"implemented": False, "reason": "pades advanced verification not wired"}
