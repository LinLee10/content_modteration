"""Rule-based detectors for moderation."""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Dict, List, Optional

from .config import LABELS

LINK_REGEX = re.compile(r"https?://\S+|www\.\S+")


class RuleResult:
    """Container for rule evaluation outputs."""

    def __init__(
        self,
        label_scores: Dict[str, float],
        reasons: List[str],
        hard_label: Optional[str] = None,
        rule_hits: Optional[List[str]] = None,
        category_hits: Optional[List[Dict[str, Any]]] = None,
    ):
        self.label_scores = label_scores
        self.reasons = reasons
        self.hard_label = hard_label
        self.rule_hits = rule_hits or []
        self.category_hits = category_hits or []

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "label_scores": self.label_scores,
            "reasons": self.reasons,
            "rule_hits": self.rule_hits,
            "category_hits": self.category_hits,
        }
        if self.hard_label:
            data["hard_label"] = self.hard_label
        return data


def _uppercase_ratio(text: str) -> float:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 0.0
    uppercase = [c for c in letters if c.isupper()]
    return len(uppercase) / len(letters)


def _compile_patterns(patterns: List[str]) -> List[re.Pattern[str]]:
    return [re.compile(pattern, flags=re.IGNORECASE) for pattern in patterns]


def evaluate_rules(text: str, config: Dict[str, Any], raw_text: Optional[str] = None) -> RuleResult:
    """Evaluate allow/deny lists, category patterns, and spam heuristics."""

    label_scores = {label: 0.0 for label in LABELS}
    reasons: List[str] = []
    rule_hits: List[str] = []
    category_hits: List[Dict[str, Any]] = []

    # Hard allow list overrides everything (regex patterns).
    for pattern in _compile_patterns(config.get("allowlist", [])):
        if pattern.search(text):
            label_scores["safe"] = 1.0
            reasons.append(f"allowlist pattern: {pattern.pattern}")
            rule_hits.append(f"allowlist::{pattern.pattern}")
            return RuleResult(label_scores, reasons, hard_label="safe", rule_hits=rule_hits, category_hits=category_hits)

    # Hard deny list enforces harmful outcome (regex patterns).
    for pattern in _compile_patterns(config.get("denylist", [])):
        if pattern.search(text):
            label_scores["harmful"] = 1.0
            reasons.append(f"denylist pattern: {pattern.pattern}")
            rule_hits.append(f"denylist::{pattern.pattern}")
            return RuleResult(label_scores, reasons, hard_label="harmful", rule_hits=rule_hits, category_hits=category_hits)

    # Category regex patterns.
    for label, patterns in config.get("category_patterns", {}).items():
        for pattern in _compile_patterns(patterns):
            if pattern.search(text):
                label_scores[label] = max(label_scores[label], 0.8)
                reasons.append(f"pattern matched for {label}: {pattern.pattern}")
                category_hits.append({"label": label, "pattern": pattern.pattern})

    # Spam heuristics
    spam_conf = config.get("spam", {})
    spam_source_text = raw_text if raw_text is not None else text
    link_count = len(LINK_REGEX.findall(spam_source_text))
    if link_count > 0:
        label_scores["spam"] = max(label_scores["spam"], float(spam_conf.get("url_presence_score", 0.4)))
        reasons.append("contains URLs")
        rule_hits.append("spam::url_presence")

    suspicious_tlds = spam_conf.get("suspicious_tlds", [])
    if suspicious_tlds and link_count:
        urls = LINK_REGEX.findall(spam_source_text)
        if any(any(url.lower().endswith(f".{tld}") or f".{tld}/" in url.lower() for tld in suspicious_tlds) for url in urls):
            label_scores["spam"] = max(label_scores["spam"], 0.7)
            reasons.append("suspicious TLD detected")
            rule_hits.append("spam::suspicious_tld")

    if link_count > spam_conf.get("max_link_count", 2):
        label_scores["spam"] = max(label_scores["spam"], 0.9)
        reasons.append("excessive links detected")
        rule_hits.append("spam::link_count")

    tokens = text.split()
    counts = Counter(tokens)
    if counts and counts.most_common(1)[0][1] >= spam_conf.get("repetition_threshold", 3):
        label_scores["spam"] = max(label_scores["spam"], 0.85)
        reasons.append("repeated tokens detected")
        rule_hits.append("spam::repetition")

    uppercase_source = raw_text if raw_text is not None else text
    if _uppercase_ratio(uppercase_source) > spam_conf.get("uppercase_ratio", 0.6):
        label_scores["spam"] = max(label_scores["spam"], 0.7)
        reasons.append("high uppercase ratio")
        rule_hits.append("spam::uppercase_ratio")

    return RuleResult(label_scores, reasons, rule_hits=rule_hits, category_hits=category_hits)

