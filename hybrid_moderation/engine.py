"""Main hybrid moderation engine."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .config import LABELS, load_config
from .preprocessing import preprocess_text
from .rules import evaluate_rules
from .arbitration import arbitrate


class HybridModerationEngine:
    """Hybrid moderation engine combining rules and optional ML scores."""

    def __init__(self, config_path: Optional[str] = None, overrides: Optional[Dict[str, Any]] = None):
        self.config = load_config(config_path, overrides)

    def _sanitize_scores(self, ml_scores: Optional[Dict[str, float]]) -> Optional[Dict[str, float]]:
        if ml_scores is None:
            return None
        allowed_labels = set(self.config.get("labels", LABELS))
        return {label: float(score) for label, score in ml_scores.items() if label in allowed_labels}

    def moderate(self, text: str, ml_scores: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        prep_options = self.config.get("preprocessing", {})
        processed_text = preprocess_text(text, prep_options)

        rule_result = evaluate_rules(processed_text, self.config, raw_text=text)
        decision = arbitrate(rule_result, self._sanitize_scores(ml_scores), self.config)

        return {
            "input": text,
            "processed": processed_text,
            "decision": decision,
        }

