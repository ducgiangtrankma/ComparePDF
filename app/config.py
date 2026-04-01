import os
from pathlib import Path

# Load .env from project root (so uvicorn and test_local pick up OPENAI_API_KEY)
_env_path = Path(__file__).resolve().parent.parent / ".env"
try:
    from dotenv import load_dotenv

    load_dotenv(_env_path)
except ImportError:
    pass

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

SHAREPOINT_WEB_URL = os.getenv("SHAREPOINT_WEB_URL", "").strip()
SHAREPOINT_FETCH_MODE = os.getenv("SHAREPOINT_FETCH_MODE", "power_automate").strip()
SHAREPOINT_FETCH_URL = os.getenv("SHAREPOINT_FETCH_URL", "").strip()
SHAREPOINT_LIST_URL = os.getenv("SHAREPOINT_LIST_URL", "").strip()
SHAREPOINT_DELETE_URL = os.getenv("SHAREPOINT_DELETE_URL", "").strip()
SHAREPOINT_USERNAME = os.getenv("SHAREPOINT_USERNAME", "").strip()
SHAREPOINT_PASSWORD = os.getenv("SHAREPOINT_PASSWORD", "").strip()
