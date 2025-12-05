import json
import subprocess
import sys

import pytest

from hybrid_moderation.engine import HybridModerationEngine


def test_allowlist_short_circuit():
    engine = HybridModerationEngine()
    result = engine.moderate("Thank you for your help!")
    decision = result["decision"]
    assert decision["label"] == "safe"
    assert decision["confidence"] == 1.0
    assert any("allowlist" in r for r in decision["reasons"])
    assert "allowlist::thank you" in decision["rule_hits"]


def test_hard_denylist_short_circuit():
    engine = HybridModerationEngine()
    result = engine.moderate("We should KILL them with sticks")
    decision = result["decision"]
    assert decision["label"] == "harmful"
    assert decision["confidence"] == 1.0
    assert decision["rule_hits"] == ["denylist::kill"]


def test_allowlist_and_denylist_use_regex_patterns():
    engine = HybridModerationEngine(
        overrides={"allowlist": [r"^ok$"], "denylist": [r"scam+mer?"]}
    )

    safe_decision = engine.moderate("OK")["decision"]
    assert safe_decision["label"] == "safe"
    assert "allowlist pattern: ^ok$" in safe_decision["reasons"]

    harmful_decision = engine.moderate("This is a scammmmer alert")["decision"]
    assert harmful_decision["label"] == "harmful"
    assert "denylist pattern: scam+mer?" in harmful_decision["reasons"]


def test_tie_margin_uses_edge_case_label():
    engine = HybridModerationEngine()
    ml_scores = {"spam": 0.4, "harmful": 0.38}
    result = engine.moderate("A regular message", ml_scores=ml_scores)
    decision = result["decision"]
    assert decision["label"] == "edge_cases"
    assert "scores within tie margin" in decision["reasons"]
    # Ensure merged scores include ML signals
    assert decision["label_scores"]["spam"] == pytest.approx(0.4)


def test_preprocessing_applied():
    engine = HybridModerationEngine(
        overrides={
            "preprocessing": {
                "lowercase": True,
                "strip_urls": True,
                "normalize_whitespace": True,
            }
        }
    )
    result = engine.moderate("HeLLo   WORLD!!!   visit http://spam.ru")
    assert result["processed"] == "hello world!!! visit"


def test_cli_outputs_rationale_and_hits(tmp_path):
    scores_file = tmp_path / "scores.json"
    scores_file.write_text(json.dumps({"spam": 0.2}), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "-m", "hybrid_moderation.cli", "--scores-file", str(scores_file)],
        input="Visit http://example.info now!!!",
        text=True,
        capture_output=True,
        check=True,
    )
    payload = json.loads(completed.stdout)
    decision = payload["decision"]
    assert "rationale" in decision and decision["rationale"]
    assert "rule_hits" in decision
    assert "category_hits" in decision
    assert any("spam::" in hit for hit in decision["rule_hits"])


if __name__ == "__main__":
    pytest.main([__file__])
