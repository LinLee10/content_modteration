"""Command-line interface for the hybrid moderation engine."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .engine import HybridModerationEngine


def _parse_scores(raw: str) -> Dict[str, float]:
    try:
        loaded = json.loads(raw)
        return {str(k): float(v) for k, v in loaded.items()}
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise argparse.ArgumentTypeError(f"Invalid JSON for scores: {exc}")


def _load_scores_file(path: str) -> Dict[str, float]:
    file_path = Path(path)
    if not file_path.exists():  # pragma: no cover - CLI validation
        raise argparse.ArgumentTypeError(f"Scores file not found: {path}")
    try:
        return _parse_scores(file_path.read_text(encoding="utf-8"))
    except OSError as exc:  # pragma: no cover - defensive
        raise argparse.ArgumentTypeError(f"Could not read scores file: {exc}")


def main(argv: Any = None) -> int:
    parser = argparse.ArgumentParser(description="Hybrid content moderation CLI")
    parser.add_argument("--config", help="Path to JSON config file", default=None)

    score_group = parser.add_mutually_exclusive_group()
    score_group.add_argument("--scores", type=_parse_scores, help="Optional JSON string with ML scores", default=None)
    score_group.add_argument("--scores-file", help="Path to JSON file containing ML scores", default=None)
    args = parser.parse_args(argv)

    text = sys.stdin.read()
    ml_scores: Optional[Dict[str, float]] = args.scores
    if args.scores_file:
        ml_scores = _load_scores_file(args.scores_file)

    engine = HybridModerationEngine(config_path=args.config)
    decision = engine.moderate(text, ml_scores=ml_scores)
    sys.stdout.write(json.dumps(decision, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

