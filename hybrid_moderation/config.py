"""Configuration utilities for the hybrid moderation engine."""
from __future__ import annotations

import json
import copy
from pathlib import Path
from typing import Any, Dict, Optional

LABELS = [
    "safe",
    "harmful",
    "false_information",
    "spam",
    "edge_cases",
]

DEFAULT_CONFIG: Dict[str, Any] = {
    "labels": LABELS,
    "preprocessing": {
        "lowercase": True,
        "strip_urls": True,
        "normalize_whitespace": True,
    },
    "allowlist": [
        "thank you",
        "have a nice day",
    ],
    "denylist": [
        "kill",
        "hate",
    ],
    "category_patterns": {
        "harmful": [r"\bhate\b", r"\bkill(ing)?\b", r"\battack\b"],
        "false_information": [r"flat earth", r"moon landing was fake"],
        "spam": [r"free money", r"visit .* now"],
    },
    "spam": {
        "max_link_count": 2,
        "repetition_threshold": 3,
        "uppercase_ratio": 0.6,
        "url_presence_score": 0.4,
        "suspicious_tlds": ["ru", "cn", "tk", "info"],
    },
    "arbitration": {
        "tie_margin": 0.05,
        "min_label_score": 0.35,
        "default_label": "safe",
    },
}


def _deep_update(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively update a dictionary without mutating the original."""
    merged = copy.deepcopy(base)
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_update(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_config(path: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Load configuration from JSON file and merge with defaults.

    Args:
        path: Optional path to a JSON configuration file.
        overrides: Optional dictionary of values to override.

    Returns:
        A configuration dictionary with defaults applied.
    """

    config = copy.deepcopy(DEFAULT_CONFIG)

    if path:
        config_path = Path(path)
        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as f:
                file_config = json.load(f)
            config = _deep_update(config, file_config)

    if overrides:
        config = _deep_update(config, overrides)

    return config

