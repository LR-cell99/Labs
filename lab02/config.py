"""
config.py — Central Configuration Layer
========================================
Loads all runtime parameters from environment variables (via .env).
Acts as the single source of truth for configuration across the application.

Usage:
    from config import GEMINI_API_KEY, MODEL_NAME, DB_NAME
"""

import os
import sys
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env into the process environment.
# override=False means real shell env vars take precedence over .env values,
# which is the safe production-friendly default.
# ---------------------------------------------------------------------------
load_dotenv(override=False)

# ---------------------------------------------------------------------------
# API Configuration
# ---------------------------------------------------------------------------
GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")

# ---------------------------------------------------------------------------
# Model Configuration
# ---------------------------------------------------------------------------
MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-1.5-pro")

# ---------------------------------------------------------------------------
# Database Configuration
# ---------------------------------------------------------------------------
DB_NAME: str = os.getenv("DB_NAME", "app_database")

# ---------------------------------------------------------------------------
# Safety Gate — halt immediately if critical credentials are absent.
# This runs at import time so any module that does `from config import ...`
# will fail fast before any network or database calls are attempted.
# ---------------------------------------------------------------------------
if GEMINI_API_KEY is None:
    print(
        "[FATAL] GEMINI_API_KEY is not set.\n"
        "        Set it in your .env file or as a shell environment variable.\n"
        "        Example (.env):  GEMINI_API_KEY=AIza...\n"
        "        Halting to prevent unauthenticated API calls.",
        file=sys.stderr,
    )
    sys.exit(1)