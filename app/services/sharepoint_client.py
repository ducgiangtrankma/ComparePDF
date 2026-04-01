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
from app.exceptions import SharePointError


def _normalize_location(location: str) -> str:
    return location.strip().replace("\\", "/").lstrip("/")


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
