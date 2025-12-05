"""Arbitration utilities for combining signals."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .config import LABELS
from .rules import RuleResult


class ArbitrationResult(Dict[str, Any]):
    """Dictionary subclass describing the final moderation decision."""

    label: str
    confidence: float
    label_scores: Dict[str, float]
    reasons: list
    rule_hits: list
    category_hits: list


def _merge_scores(rule_scores: Dict[str, float], ml_scores: Optional[Dict[str, float]]) -> Dict[str, float]:
    merged = dict(rule_scores)
    if ml_scores:
        for label, score in ml_scores.items():
            if label in merged:
                merged[label] = max(merged[label], float(score))
    return merged


def _top_two(scores: Dict[str, float]) -> Tuple[Tuple[str, float], Tuple[str, float]]:
    sorted_pairs = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top = sorted_pairs[0]
    second = sorted_pairs[1] if len(sorted_pairs) > 1 else ("", 0.0)
    return top, second


def arbitrate(rule_result: RuleResult, ml_scores: Optional[Dict[str, float]], config: Dict[str, Any]) -> ArbitrationResult:
    """Combine rules and ML scores to produce a final decision."""
    if rule_result.hard_label:
        return ArbitrationResult(
            label=rule_result.hard_label,
            confidence=1.0,
            label_scores=rule_result.label_scores,
            reasons=rule_result.reasons,
            rationale=rule_result.reasons,
            rule_hits=rule_result.rule_hits,
            category_hits=rule_result.category_hits,
            source="rules",
        )

    merged_scores = _merge_scores(rule_result.label_scores, ml_scores)
    for label in LABELS:
        merged_scores.setdefault(label, 0.0)

    top, second = _top_two(merged_scores)
    tie_margin = config.get("arbitration", {}).get("tie_margin", 0.05)
    min_label_score = config.get("arbitration", {}).get("min_label_score", 0.35)
    default_label = config.get("arbitration", {}).get("default_label", "safe")

    # Tie-breaker handling
    if top[1] - second[1] < tie_margin:
        return ArbitrationResult(
            label="edge_cases",
            confidence=top[1],
            label_scores=merged_scores,
            reasons=rule_result.reasons + ["scores within tie margin"],
            rationale=rule_result.reasons + ["scores within tie margin"],
            rule_hits=rule_result.rule_hits,
            category_hits=rule_result.category_hits,
            source="hybrid",
        )

    if top[1] < min_label_score:
        return ArbitrationResult(
            label=default_label,
            confidence=min_label_score,
            label_scores=merged_scores,
            reasons=rule_result.reasons + ["below minimum score"],
            rationale=rule_result.reasons + ["below minimum score"],
            rule_hits=rule_result.rule_hits,
            category_hits=rule_result.category_hits,
            source="hybrid",
        )

    return ArbitrationResult(
        label=top[0],
        confidence=top[1],
        label_scores=merged_scores,
        reasons=rule_result.reasons + ["combined arbitration"],
        rationale=rule_result.reasons + ["combined arbitration"],
        rule_hits=rule_result.rule_hits,
        category_hits=rule_result.category_hits,
        source="hybrid",
    )

