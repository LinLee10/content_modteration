"""Text preprocessing helpers."""
from __future__ import annotations

import re
from typing import Dict

URL_REGEX = re.compile(r"https?://\S+|www\.\S+")
PUNCT_REGEX = re.compile(r"[\.,;:!?]+")


def preprocess_text(text: str, options: Dict[str, bool]) -> str:
    """Apply configurable preprocessing to text.

    Supported options:
    - lowercase: convert text to lowercase
    - strip_urls: remove URLs
    - normalize_whitespace: collapse whitespace
    """

    processed = text
    if options.get("lowercase", False):
        processed = processed.lower()

    if options.get("strip_urls", False):
        processed = URL_REGEX.sub("", processed)

    if options.get("normalize_whitespace", False):
        processed = re.sub(r"\s+", " ", processed).strip()

    return processed

