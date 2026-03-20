from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from app.config import load_settings
from evaluation.cs_reference_eval import run_cs_reference_eval


def main() -> None:
    parser = argparse.ArgumentParser(description="Run CS subset reference recovery evaluation.")
    parser.add_argument("--work-root", default="tmp/cs_eval", help="Workspace for copied notes, temp indexes and reports.")
    parser.add_argument("--threshold", type=float, default=None, help="Override retrieval.threshold for this eval run.")
    parser.add_argument("--top-k", type=int, default=None, help="Override retrieval.top_k for this eval run.")
    parser.add_argument("--top-k-ann", type=int, default=None, help="Override retrieval.top_k_ann for this eval run.")
    parser.add_argument("--max-hits-per-note", type=int, default=None, help="Override retrieval.max_hits_per_note.")
    parser.add_argument("--note-diversity-penalty", type=float, default=None, help="Override retrieval.note_diversity_penalty.")
    parser.add_argument("--min-content-anchor", type=float, default=None, help="Override retrieval.min_content_anchor.")
    parser.add_argument(
        "--semantic-only-anchor-floor",
        type=float,
        default=None,
        help="Override retrieval.semantic_only_anchor_floor.",
    )
    parser.add_argument(
        "--anchor-penalty-strength",
        type=float,
        default=None,
        help="Override retrieval.anchor_penalty_strength.",
    )
    args = parser.parse_args()

    settings = load_settings()
    retrieval_overrides = {
        "threshold": args.threshold,
        "top_k": args.top_k,
        "top_k_ann": args.top_k_ann,
        "max_hits_per_note": args.max_hits_per_note,
        "note_diversity_penalty": args.note_diversity_penalty,
        "min_content_anchor": args.min_content_anchor,
        "semantic_only_anchor_floor": args.semantic_only_anchor_floor,
        "anchor_penalty_strength": args.anchor_penalty_strength,
    }
    retrieval_overrides = {key: value for key, value in retrieval_overrides.items() if value is not None}
    report = run_cs_reference_eval(
        settings=settings,
        work_root=Path(args.work_root),
        retrieval_overrides=retrieval_overrides or None,
    )
    print(
        json.dumps(
            {
                "metrics": report["metrics"],
                "retrieval_config": report["retrieval_config"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(f"report.json: {Path(args.work_root) / 'reports' / 'report.json'}")
    print(f"report.md: {Path(args.work_root) / 'reports' / 'report.md'}")


if __name__ == "__main__":
    main()
