import base64
from typing import Any

import requests

from app.config import (
    SHAREPOINT_FETCH_MODE,
    SHAREPOINT_FETCH_URL,
    SHAREPOINT_LIST_URL,
    SHAREPOINT_PASSWORD,
    SHAREPOINT_USERNAME,
    SHAREPOINT_WEB_URL,
)
from app.exceptions import SharePointError, SharePointFolderRuleError


def _normalize_location(location: str) -> str:
    return location.strip().replace("\\", "/").lstrip("/")


def _entry_basename(entry: str) -> str:
    return _normalize_location(entry).split("/")[-1]


def validate_sharepoint_compare_paths(location_a: str, location_b: str) -> None:
    """Both locations must point to a file whose name ends with .pdf."""
    for loc, label in ((location_a, "location_a"), (location_b, "location_b")):
        base = _entry_basename(loc)
        if not base:
            raise SharePointFolderRuleError(f"{label} không hợp lệ (rỗng).")
        if not base.lower().endswith(".pdf"):
            raise SharePointFolderRuleError(
                f"{label} phải trỏ tới file PDF (.pdf): {loc!r}"
            )


def validate_sharepoint_folder_listing(names: list[str]) -> list[str]:
    """Same rules as local interactive folder: only PDFs; 1 or 2 files (not 0, not >2)."""
    trimmed = [str(n).strip() for n in names if n is not None and str(n).strip()]
    if not trimmed:
        raise SharePointFolderRuleError("Thư mục SharePoint không có file nào.")

    non_pdf = [n for n in trimmed if not _entry_basename(n).lower().endswith(".pdf")]
    if non_pdf:
        preview = ", ".join(non_pdf[:15])
        more = " …" if len(non_pdf) > 15 else ""
        raise SharePointFolderRuleError(
            "Chỉ chấp nhận file PDF trong thư mục. "
            f"File không phải PDF: {preview}{more}"
        )

    if len(trimmed) > 2:
        preview = ", ".join(trimmed[:10])
        more = " …" if len(trimmed) > 10 else ""
        raise SharePointFolderRuleError(
            f"Thư mục chỉ được có tối đa 2 file PDF (hiện có {len(trimmed)}): {preview}{more}"
        )

    return trimmed


def _extract_base64_from_response(raw_text: str, json_obj: Any) -> str:
    if raw_text:
        text = raw_text.strip().strip('"')
        if text and not text.startswith("{"):
            return text

    if isinstance(json_obj, dict):
        for key in ("content", "fileContent", "base64", "data", "body"):
            val = json_obj.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip().strip('"')

    raise SharePointError("SharePoint response does not contain base64 content.")


def _download_via_power_automate(web_url: str, location: str) -> bytes:
    if not SHAREPOINT_FETCH_URL:
        raise SharePointError("Missing SHAREPOINT_FETCH_URL for power_automate mode.")

    payload = {"url": web_url, "location": location}
    try:
        resp = requests.post(SHAREPOINT_FETCH_URL, json=payload, timeout=60)
    except requests.RequestException as exc:
        raise SharePointError(
            "Cannot connect to SHAREPOINT_FETCH_URL. "
            "Please check .env value and network/DNS access."
        ) from exc
    if not resp.ok:
        raise SharePointError(
            f"Power Automate fetch failed ({resp.status_code}): {resp.text[:300]}"
        )

    try:
        json_obj = resp.json()
    except ValueError:
        json_obj = None

    b64 = _extract_base64_from_response(resp.text, json_obj)
    try:
        return base64.b64decode(b64)
    except Exception as exc:
        raise SharePointError("Invalid base64 content returned from SharePoint flow.") from exc


def _download_via_rest(web_url: str, location: str) -> bytes:
    if not SHAREPOINT_USERNAME or not SHAREPOINT_PASSWORD:
        raise SharePointError(
            "Missing SHAREPOINT_USERNAME/SHAREPOINT_PASSWORD for rest mode."
        )

    endpoint = f"{web_url.rstrip('/')}/_api/web/GetFileByServerRelativeUrl('{location}')/$value"
    try:
        resp = requests.get(
            endpoint,
            auth=(SHAREPOINT_USERNAME, SHAREPOINT_PASSWORD),
            headers={"X-FORMS_BASED_AUTH_ACCEPTED": "f"},
            timeout=60,
        )
    except requests.RequestException as exc:
        raise SharePointError(
            "Cannot connect to SharePoint REST endpoint. "
            "Please check SHAREPOINT_WEB_URL and network/DNS access."
        ) from exc
    if not resp.ok:
        raise SharePointError(
            f"SharePoint REST download failed ({resp.status_code}): {resp.text[:300]}"
        )
    return resp.content


def download_sharepoint_file(
    location: str, web_url: str | None = None, fetch_mode: str | None = None
) -> bytes:
    mode = (fetch_mode or SHAREPOINT_FETCH_MODE or "power_automate").strip()
    sp_web_url = (web_url or SHAREPOINT_WEB_URL).strip()
    if not sp_web_url:
        raise SharePointError("Missing SharePoint web URL. Provide web_url or SHAREPOINT_WEB_URL.")

    norm_location = _normalize_location(location)
    if not norm_location:
        raise SharePointError("SharePoint location is empty.")

    if mode == "power_automate":
        return _download_via_power_automate(sp_web_url, norm_location)
    if mode == "rest":
        return _download_via_rest(sp_web_url, norm_location)

    raise SharePointError(f"Unsupported fetch_mode '{mode}'. Use 'power_automate' or 'rest'.")


def list_sharepoint_files(
    folder_location: str, web_url: str | None = None, typefile: str = "pdf"
) -> list[str]:
    """List file names in a SharePoint folder via Power Automate endpoint.

    Follows the same payload shape as C#:
    {"url": web_url, "location": "/<folder>", "typefile": "<type>"}
    """
    if not SHAREPOINT_LIST_URL:
        raise SharePointError("Missing SHAREPOINT_LIST_URL for list files operation.")

    sp_web_url = (web_url or SHAREPOINT_WEB_URL).strip()
    if not sp_web_url:
        raise SharePointError("Missing SharePoint web URL. Provide web_url or SHAREPOINT_WEB_URL.")

    location = _normalize_location(folder_location)
    payload = {
        "url": sp_web_url,
        "location": f"/{location}",
        "typefile": typefile or "all",
    }

    try:
        resp = requests.post(SHAREPOINT_LIST_URL, json=payload, timeout=60)
    except requests.RequestException as exc:
        raise SharePointError(
            "Cannot connect to SHAREPOINT_LIST_URL. "
            "Please check .env value and network/DNS access."
        ) from exc
    if not resp.ok:
        raise SharePointError(
            f"Power Automate list files failed ({resp.status_code}): {resp.text[:300]}"
        )

    text = resp.text.strip()
    if not text:
        return []

    # C# implementation expects comma-separated names from PA response.
    if "," in text:
        items = [item.strip() for item in text.split(",")]
        return [item for item in items if item]

    # Fallback for JSON responses.
    try:
        data = resp.json()
    except ValueError:
        return [text]

    if isinstance(data, list):
        return [str(x).strip() for x in data if str(x).strip()]
    if isinstance(data, dict):
        for key in ("files", "data", "items", "body"):
            val = data.get(key)
            if isinstance(val, list):
                return [str(x).strip() for x in val if str(x).strip()]
            if isinstance(val, str):
                parts = [item.strip() for item in val.split(",")]
                return [item for item in parts if item]
    return []
