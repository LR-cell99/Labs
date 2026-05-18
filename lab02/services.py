"""
services.py — Infrastructure / API Layer
=========================================================
Owns all outbound communication with the Google Gemini cloud API.
No business logic, no database calls — only prompt construction,
network I/O, and raw response parsing live here.

The module-level `client` is initialised once at import time using
the key already validated by config.py, so callers never handle
credentials directly.

Typical usage:
    from services.gemini_service import analyze_review_sentiment

    result = analyze_review_sentiment("The product broke after one day.")
    print(result)
    # {
    #   "rating":   2,
    #   "category": "Bad",
    #   "raw":      "Rating: 2\nCategory: Bad\nReason: ..."
    # }
"""

import re
import sys
import google.generativeai as genai

from config import GEMINI_API_KEY, MODEL_NAME

# ---------------------------------------------------------------------------
# Client initialisation — runs once when the module is first imported.
# config.py has already called sys.exit(1) if the key is absent, so
# GEMINI_API_KEY is guaranteed to be a non-None string here.
# ---------------------------------------------------------------------------
genai.configure(api_key=GEMINI_API_KEY)

_client = genai.GenerativeModel(
    model_name=MODEL_NAME,
    # System-level instructions are set at model construction time so they
    # are not repeated in every user-facing prompt payload.
    system_instruction="""
You are a strict sentiment analysis engine. Your sole task is to evaluate
customer review text and return a structured assessment with EXACTLY this
format — no extra prose, no markdown, no preamble:

Rating: <integer 1-5>
Category: <Good|Average|Bad>
Reason: <one concise sentence>

Rating scale:
  5 — Exceptional, enthusiastic praise
  4 — Positive with minor reservations
  3 — Neutral or mixed
  2 — Negative with some positives
  1 — Strongly negative, no redeeming points

Category mapping:
  Good    → Rating 4 or 5
  Average → Rating 3
  Bad     → Rating 1 or 2

Never deviate from this output format. Never add commentary outside the
three fields above.
""".strip(),
)

# ---------------------------------------------------------------------------
# Category derivation — pure function, no I/O
# ---------------------------------------------------------------------------

def _derive_category(rating: int) -> str:
    """
    Map a 1-5 integer rating to its classification bucket.

    4-5  → Good
    3    → Average
    1-2  → Bad
    """
    if rating >= 4:
        return "Good"
    if rating == 3:
        return "Average"
    return "Bad"


# ---------------------------------------------------------------------------
# Response parser — pure function, no I/O
# ---------------------------------------------------------------------------

def _parse_response(raw_text: str) -> tuple[int, str]:
    """
    Extract the rating integer and category string from the model's
    structured plain-text response.

    Falls back gracefully:
    - If the model omits the Category line, derive it from the rating.
    - If the Rating line is missing entirely, raises ValueError so the
      caller can decide how to handle the failure.

    Parameters
    ----------
    raw_text : The complete text block returned by the Gemini model.

    Returns
    -------
    (rating, category) : (int, str)
    """
    # Extract Rating
    rating_match = re.search(r"Rating:\s*([1-5])", raw_text)
    if not rating_match:
        raise ValueError(
            f"Could not extract a valid 1-5 rating from model response:\n{raw_text}"
        )
    rating = int(rating_match.group(1))

    # Extract Category — prefer the model's own output, fall back to derived
    category_match = re.search(r"Category:\s*(Good|Average|Bad)", raw_text, re.IGNORECASE)
    category = category_match.group(1).capitalize() if category_match else _derive_category(rating)

    return rating, category


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_review_sentiment(review_content: str) -> dict:
    """
    Send *review_content* to the Gemini model and return parsed sentiment.

    Parameters
    ----------
    review_content : str
        Raw customer review text of any length.

    Returns
    -------
    dict with keys:
        "rating"   (int)  — 1-5 numeric score
        "category" (str)  — "Good" | "Average" | "Bad"
        "raw"      (str)  — Full unmodified model response (useful for logs)

    Raises
    ------
    ValueError
        If the model response cannot be parsed into a valid rating.
    google.api_core.exceptions.GoogleAPIError
        Propagated as-is if the network call fails — let the caller decide
        whether to retry or surface the error to the user.
    """
    if not review_content or not review_content.strip():
        raise ValueError("review_content must be a non-empty string.")

    response = _client.generate_content(review_content)
    raw_text = response.text.strip()

    rating, category = _parse_response(raw_text)

    return {
        "rating":   rating,
        "category": category,
        "raw":      raw_text,
    }