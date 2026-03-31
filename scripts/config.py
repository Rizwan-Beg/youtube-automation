"""
config.py — Centralised configuration for YouTube Auto Factory.

Loads environment variables from .env and exposes typed constants
for directories, credentials, and pipeline settings.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# Directory Paths
# ---------------------------------------------------------------------------
VIDEOS_RAW_DIR = PROJECT_ROOT / "videos_raw"
VIDEOS_CLEAN_DIR = PROJECT_ROOT / "videos_clean"
THUMBNAILS_DIR = PROJECT_ROOT / "thumbnails"
METADATA_DIR = PROJECT_ROOT / "metadata"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure all directories exist
for d in [
    VIDEOS_RAW_DIR, VIDEOS_CLEAN_DIR, THUMBNAILS_DIR, METADATA_DIR, LOGS_DIR,
]:
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Topics
# ---------------------------------------------------------------------------
TOPICS_FILE = PROJECT_ROOT / "topics.json"
PROCESSED_TOPICS_FILE = PROJECT_ROOT / "processed_topics.json"

# ---------------------------------------------------------------------------
# Google / YouTube
# ---------------------------------------------------------------------------
GOOGLE_CLIENT_SECRET_FILE = os.getenv(
    "GOOGLE_CLIENT_SECRET_FILE", str(PROJECT_ROOT / "client_secret.json")
)
YOUTUBE_CATEGORY_ID = os.getenv("YOUTUBE_CATEGORY_ID", "27")

# Cached OAuth token
YOUTUBE_TOKEN_FILE = str(PROJECT_ROOT / "token.json")

# ---------------------------------------------------------------------------
# Ollama (Local LLM)
# ---------------------------------------------------------------------------
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------
SCHEDULE_TIME = os.getenv("SCHEDULE_TIME", "10:00")

# ---------------------------------------------------------------------------
# Gemini (for Imagen 3 Thumbnails)
# ---------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ---------------------------------------------------------------------------
# Pipeline Flags
# ---------------------------------------------------------------------------
DRY_RUN = os.getenv("DRY_RUN", "false").lower() == "true"
NOTEBOOKLM_MAX_RETRIES = int(os.getenv("NOTEBOOKLM_MAX_RETRIES", "3"))
NOTEBOOKLM_TIMEOUT = int(os.getenv("NOTEBOOKLM_TIMEOUT", "1800"))

# ---------------------------------------------------------------------------
# Video Overlay
# ---------------------------------------------------------------------------
CHANNEL_NAME = os.getenv("CHANNEL_NAME", "MyChannel")
OVERLAY_TEXT = os.getenv("OVERLAY_TEXT", "Subscribe & Like ❤️")

# ---------------------------------------------------------------------------
# Playwright — persistent browser data directory
# ---------------------------------------------------------------------------
BROWSER_DATA_DIR = PROJECT_ROOT / ".browser_data"
BROWSER_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FILE = LOGS_DIR / "pipeline.log"
